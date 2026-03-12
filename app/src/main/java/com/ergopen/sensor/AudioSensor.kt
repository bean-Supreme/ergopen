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

                        Log.d(TAG, "freq=${freqHz.toInt()}Hz rpm=${rpm.toInt()} watts=${watts.toInt()} rms=${rms.toInt()} active=$active")

                        emit(RowerPacket.Instantaneous(
                            timestamp = System.currentTimeMillis(),
                            rpm = rpm,
                            revolutions = totalFrames / SAMPLE_RATE.toFloat(),
                            watts = watts.coerceAtLeast(0f),
                            handleMm = freqHz.toInt(), // raw Hz for calibration
                            sequence = sequence++
                        ))

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
