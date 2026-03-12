package com.hydropen.sensor

import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.math.sin

object FakeSensor {

    fun packets(): Flow<RowerPacket> = flow {
        var seq = 0
        var revolutions = 0f

        while (true) {
            val t = seq * 0.1
            val rpm = 24f + (8f * sin(t).toFloat())
            revolutions += rpm / 600f
            val watts = rpm * rpm * 0.4f

            emit(RowerPacket.Instantaneous(
                timestamp = System.currentTimeMillis(),
                rpm = rpm,
                revolutions = revolutions,
                watts = watts,
                handleMm = (500 + (200 * sin(t + 1.0)).toInt()),
                sequence = seq
            ))

            if (seq > 0 && seq % 20 == 0) {
                emit(RowerPacket.Stroke(
                    timestamp = System.currentTimeMillis(),
                    startPosition = 300,
                    endPosition = 700,
                    driveRevolutions = 1.2f,
                    recoveryRevolutions = 2.1f,
                    averageWatts = watts,
                    lastPacketRecoveryEndIndex = seq - 10,
                    driveEndIndex = seq - 5,
                    sequence = seq
                ))
            }

            seq++
            delay(100)
        }
    }
}
