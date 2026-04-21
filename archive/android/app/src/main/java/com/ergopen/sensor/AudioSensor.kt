package com.ergopen.sensor

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import java.io.File
import java.io.FileOutputStream
import kotlin.math.sqrt
import kotlin.math.abs

object AudioSensor {

    private const val TAG = "AudioSensor"
    private const val SAMPLE_RATE = 44100
    private const val ENCODING = AudioFormat.ENCODING_PCM_16BIT
    private const val MAX_FILE_BYTES = 5 * 1024 * 1024 // 5MB cap

    // Calibration constants — tune these while rowing
    // PULSES_PER_REV: how many signal cycles per flywheel revolution
    // Start at 60 (plausible for a multi-pole sensor); halve or double if RPM feels off
    const val PULSES_PER_REV = 60f

    // Watts = POWER_K * (rev/s)^3 — flywheel power curve
    // Tune until displayed watts match perceived effort
    const val POWER_K = 4.0f

    // RMS below this = noise, output zeros
    private const val NOISE_THRESHOLD = 500f

    // Stroke detection — valley-based, works at any cadence
    // A stroke fires at the bottom of each recovery dip: when frequency was falling
    // for at least 2 consecutive windows and then starts rising again.
    // Much more robust than a fixed ratio at high cadence where the flywheel
    // barely decelerates between strokes.
    private const val MIN_DRIVE_HZ     = 160f  // peak must exceed this to count as a real drive
    private const val MIN_DROP_RATIO   = 0.06f // 6% drop from peak required (filters flat noise)
    private const val NOISE_MARGIN     = 0.03f // freq within 3% of prev = "not falling" (jitter guard)
    private const val MIN_DRIVE_WINDOWS = 5    // ≥5 rising windows (~500ms) required — filters blips

    // Autocorrelation pitch detector — finds fundamental frequency of complex waveforms
    // Returns frequency in Hz, or 0 if no clear pitch found
    private fun detectFrequency(buf: ShortArray, count: Int): Float {
        if (count < 2) return 0f
        val minLag = SAMPLE_RATE / 600   // max 600 Hz (flywheel won't go higher)
        val maxLag = SAMPLE_RATE / 50    // min 50 Hz

        var bestLag = -1
        var bestCorr = 0.0

        var energy = 0.0
        for (i in 0 until count) energy += buf[i].toDouble() * buf[i]
        if (energy == 0.0) return 0f

        for (lag in minLag..minOf(maxLag, count - 1)) {
            var corr = 0.0
            for (i in 0 until count - lag) {
                corr += buf[i].toDouble() * buf[i + lag]
            }
            corr /= energy
            if (corr > bestCorr) {
                bestCorr = corr
                bestLag = lag
            }
        }

        // Reject if best lag is at the boundary (edge artifact) or correlation too weak
        if (bestLag <= minLag || bestCorr < 0.3) return 0f
        return SAMPLE_RATE.toFloat() / bestLag
    }

    fun record(outputDir: File): Flow<RowerPacket> = flow {
        val channel = AudioFormat.CHANNEL_IN_MONO
        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, channel, ENCODING)
            .coerceAtLeast(8192)

        val recorder = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            SAMPLE_RATE, channel, ENCODING, bufferSize
        )
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            error("AudioRecord failed to initialize")
        }

        val outFile = File(outputDir, "signal_${System.currentTimeMillis()}.pcm")
        Log.i(TAG, "Recording to ${outFile.absolutePath}, pulsesPerRev=$PULSES_PER_REV powerK=$POWER_K")

        recorder.startRecording()

        try {
            FileOutputStream(outFile).use { fos ->
                val buf = ShortArray(bufferSize / 2)
                var totalFrames = 0L
                var bytesWritten = 0L
                var sequence = 0
                var windowSamples = 0
                val windowSize = SAMPLE_RATE / 10  // emit every 100ms
                val windowBuf = ShortArray(windowSize)
                var smoothedFreq = 0f              // exponential moving average
                val alpha = 0.3f                   // smoothing factor (lower = smoother)
                var totalRevolutions = 0f          // accumulated flywheel revolutions

                // Stroke detection state
                var peakFreq = 0f                  // highest freq seen during current drive phase
                var peakWattsSum = 0f
                var peakWindows = 0
                var driveRevs = 0f
                var recoveryRevs = 0f
                var prevRecoveryRevs = 0f
                var driveStartSeq = 0
                var strokeCount = 0
                var inRecovery = false             // true while freq is declining post-peak
                var consecutiveFalling = 0         // windows in a row freq has been declining
                var prevFreqHz = 0f                // smoothedFreq from previous window

                while (true) {
                    val read = recorder.read(buf, 0, buf.size)
                    if (read <= 0) continue

                    // Write raw PCM (capped)
                    if (bytesWritten < MAX_FILE_BYTES) {
                        val bytes = ByteArray(read * 2)
                        for (i in 0 until read) {
                            bytes[i * 2]     = (buf[i].toInt() and 0xFF).toByte()
                            bytes[i * 2 + 1] = (buf[i].toInt() shr 8 and 0xFF).toByte()
                        }
                        fos.write(bytes)
                        bytesWritten += read * 2
                    }

                    // Accumulate into window buffer, compute RMS
                    var sumSq = 0L
                    for (i in 0 until read) {
                        val s = buf[i].toInt()
                        sumSq += s.toLong() * s
                        if (windowSamples < windowBuf.size) windowBuf[windowSamples] = buf[i]
                        windowSamples++
                    }
                    totalFrames += read

                    if (windowSamples >= windowSize) {
                        val rms = sqrt(sumSq.toDouble() / read).toFloat()
                        val active = rms >= NOISE_THRESHOLD

                        val rawFreq = if (active) detectFrequency(windowBuf, windowBuf.size) else 0f
                        if (rawFreq > 0f) smoothedFreq = alpha * rawFreq + (1f - alpha) * smoothedFreq
                        else if (!active) smoothedFreq *= 0.8f  // decay toward zero when quiet
                        val freqHz = smoothedFreq
                        val rps = freqHz / PULSES_PER_REV
                        val rpm = rps * 60f
                        val watts = if (active && freqHz > 0f) POWER_K * rps * rps * rps else 0f
                        totalRevolutions += rps * (windowSize.toFloat() / SAMPLE_RATE)

                        Log.d(TAG, "freq=${freqHz.toInt()}Hz rpm=${rpm.toInt()} watts=${watts.toInt()} rms=${rms.toInt()} active=$active")

                        val revsThisWindow = rps * (windowSize.toFloat() / SAMPLE_RATE)

                        emit(RowerPacket.Instantaneous(
                            timestamp = System.currentTimeMillis(),
                            rpm = rpm,
                            revolutions = totalRevolutions,
                            watts = watts.coerceAtLeast(0f),
                            handleMm = freqHz.toInt(), // raw Hz for calibration
                            sequence = sequence
                        ))

                        // Stroke detection — valley-based
                        // Fire at the bottom of each recovery dip (falling→rising transition).
                        val rising = freqHz >= prevFreqHz * (1f - NOISE_MARGIN)
                        if (active) {
                            if (rising) {
                                // Freq is rising (or flat within noise margin)
                                if (inRecovery && consecutiveFalling >= 2) {
                                    // Turning point: was falling ≥2 windows, now rising → valley
                                    val drop = if (peakFreq > 0f) (peakFreq - prevFreqHz) / peakFreq else 0f
                                    if (peakFreq >= MIN_DRIVE_HZ && drop >= MIN_DROP_RATIO && peakWindows >= MIN_DRIVE_WINDOWS) {
                                        val avgWatts = if (peakWindows > 0) peakWattsSum / peakWindows else 0f
                                        Log.i(TAG, "Stroke #${strokeCount+1}: peak=${peakFreq.toInt()}Hz valley=${prevFreqHz.toInt()}Hz drop=${"%.0f".format(drop*100)}% driveRevs=${"%.2f".format(driveRevs)} avgWatts=${avgWatts.toInt()}")
                                        emit(RowerPacket.Stroke(
                                            timestamp = System.currentTimeMillis(),
                                            startPosition = 0,
                                            endPosition = 0,
                                            driveRevolutions = driveRevs,
                                            recoveryRevolutions = prevRecoveryRevs,
                                            averageWatts = avgWatts,
                                            lastPacketRecoveryEndIndex = driveStartSeq,
                                            driveEndIndex = sequence,
                                            sequence = strokeCount++
                                        ))
                                        prevRecoveryRevs = recoveryRevs
                                        recoveryRevs = 0f
                                        driveRevs = 0f
                                        peakFreq = 0f
                                        peakWattsSum = 0f
                                        peakWindows = 0
                                        driveStartSeq = sequence
                                    }
                                }
                                inRecovery = false
                                consecutiveFalling = 0
                                if (freqHz > peakFreq) peakFreq = freqHz
                                driveRevs += revsThisWindow
                                peakWattsSum += watts
                                peakWindows++
                            } else {
                                // Freq is falling — in recovery
                                inRecovery = true
                                consecutiveFalling++
                                recoveryRevs += revsThisWindow
                            }
                        } else {
                            // Signal lost — decay state
                            if (peakFreq > 0f) peakFreq *= 0.9f
                            if (inRecovery) consecutiveFalling++
                        }
                        prevFreqHz = freqHz

                        sequence++
                        windowSamples = 0
                    }
                }
            }
        } finally {
            recorder.stop()
            recorder.release()
            Log.i(TAG, "Stopped. Written ${outFile.length() / 1024}KB to ${outFile.name}")
        }
    }.flowOn(Dispatchers.IO)
}
