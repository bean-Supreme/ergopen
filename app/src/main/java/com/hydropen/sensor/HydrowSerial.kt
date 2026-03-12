package com.hydropen.sensor

import android_serialport_api.SerialPort
import com.hydropen.decoder.PacketDecoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import java.io.File

object ErgSerial {

    // Stock app tries these in order: ttyACM0, ttyMT1, ttyUSB0
    // ttyMT1 -> /dev/ttyS1 is the MediaTek hardware UART confirmed present on this device
    private val DEVICE_PATHS = listOf("/dev/ttyMT1", "/dev/ttyACM0", "/dev/ttyUSB0")
    private const val BAUD_RATE = 921600

    private const val CMD_CONTINUOUS_ON  = "Cm 1\n\r"
    private const val CMD_CONTINUOUS_OFF = "Cm 0\n\r"

    fun packets(): Flow<RowerPacket> = flow {
        val port = openPort()
        val input = port.inputStream
        val output = port.outputStream

        try {
            output.write(CMD_CONTINUOUS_ON.toByteArray(Charsets.US_ASCII))
            output.flush()

            val buf = StringBuilder()
            val bytes = ByteArray(512)

            while (true) {
                val n = input.read(bytes)
                if (n <= 0) continue

                buf.append(String(bytes, 0, n, Charsets.US_ASCII))

                var nl = buf.indexOf('\n')
                while (nl >= 0) {
                    val line = buf.substring(0, nl)
                    buf.delete(0, nl + 1)
                    val packet = PacketDecoder.decode(line)
                    if (packet != null) emit(packet)
                    nl = buf.indexOf('\n')
                }
            }
        } finally {
            runCatching {
                output.write(CMD_CONTINUOUS_OFF.toByteArray(Charsets.US_ASCII))
                output.flush()
            }
            runCatching { port.close() }
        }
    }.flowOn(Dispatchers.IO)

    fun setResistance(port: SerialPort, level: Int) {
        require(level in 50..200) { "Resistance $level out of safe range [50, 200]" }
        port.outputStream.write("Cl $level\n\r".toByteArray(Charsets.US_ASCII))
        port.outputStream.flush()
    }

    private fun openPort(): SerialPort {
        for (path in DEVICE_PATHS) {
            val file = File(path)
            if (file.canRead() && file.canWrite()) {
                return SerialPort(file, BAUD_RATE, 0)
            }
        }
        error("Could not open serial port at any of: $DEVICE_PATHS")
    }
}
