package com.ergopen.tools

import android.media.*
import android.os.*
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.*
import kotlin.math.*

class SignalInspectorActivity : AppCompatActivity() {

    private val sampleRate = 44100
    private var isRunning = false

    private lateinit var audioRecord: AudioRecord
    private lateinit var buffer: ShortArray

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val bufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        buffer = ShortArray(bufferSize)

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        startCapture()
    }

    private fun startCapture() {
        isRunning = true
        audioRecord.startRecording()

        CoroutineScope(Dispatchers.IO).launch {
            while (isRunning) {

                val read = audioRecord.read(buffer, 0, buffer.size)

                if (read > 0) {
                    analyzeSignal(buffer, read)
                }
            }
        }
    }

    private fun analyzeSignal(data: ShortArray, length: Int) {

        var min = Short.MAX_VALUE
        var max = Short.MIN_VALUE
        var sumSq = 0.0

        for (i in 0 until length) {
            val v = data[i]

            if (v < min) min = v
            if (v > max) max = v

            sumSq += (v * v)
        }

        val rms = sqrt(sumSq / length)

        println(
            "Signal stats -> min=$min max=$max rms=$rms"
        )
    }

    override fun onDestroy() {
        super.onDestroy()

        isRunning = false
        audioRecord.stop()
        audioRecord.release()
    }
}