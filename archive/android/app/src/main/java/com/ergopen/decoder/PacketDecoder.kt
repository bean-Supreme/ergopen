package com.ergopen.decoder

import com.ergopen.sensor.RowerPacket

object PacketDecoder {

    fun decode(line: String, timestamp: Long = System.currentTimeMillis()): RowerPacket? {
        val trimmed = line.trim()
        if (trimmed.isEmpty()) return null
        val parts = trimmed.split(" ")
        return try {
            when (parts[0]) {
                "Di"  -> parseInstantaneous(parts, timestamp)
                "Di2" -> parseInstantaneous(parts, timestamp) // V2 same format
                "Ds"  -> parseStroke(parts, timestamp)
                "Ds2" -> parseStroke(parts, timestamp)        // V2 same format
                "Rl"  -> parseResistanceLevel(parts, timestamp)
                "Rv"  -> RowerPacket.Version(timestamp, parts.drop(1).joinToString(" "))
                "Rs"  -> RowerPacket.SerialNumber(timestamp, parts.drop(1).joinToString(" "))
                "Rh"  -> RowerPacket.Health(timestamp, parts.drop(1).joinToString(" "))
                else  -> RowerPacket.Unknown(timestamp, trimmed)
            }
        } catch (e: Exception) {
            RowerPacket.Unknown(timestamp, trimmed)
        }
    }

    private fun parseInstantaneous(parts: List<String>, timestamp: Long): RowerPacket.Instantaneous {
        require(parts.size == 6) { "Di expects 6 fields, got ${parts.size}" }
        return RowerPacket.Instantaneous(
            timestamp = timestamp,
            rpm = parts[1].toInt() / 5f,
            revolutions = parts[2].toInt() / 100f,
            watts = parts[3].toInt() / 10f,
            handleMm = parts[4].toInt(),
            sequence = parts[5].toInt()
        )
    }

    private fun parseStroke(parts: List<String>, timestamp: Long): RowerPacket.Stroke {
        require(parts.size == 9) { "Ds expects 9 fields, got ${parts.size}" }
        return RowerPacket.Stroke(
            timestamp = timestamp,
            startPosition = parts[1].toInt(),
            endPosition = parts[2].toInt(),
            driveRevolutions = parts[3].toInt() / 10f,
            recoveryRevolutions = parts[4].toInt() / 10f,
            averageWatts = parts[5].toInt() / 10f,
            lastPacketRecoveryEndIndex = parts[6].toInt(),
            driveEndIndex = parts[7].toInt(),
            sequence = parts[8].toInt()
        )
    }

    private fun parseResistanceLevel(parts: List<String>, timestamp: Long): RowerPacket.ResistanceLevel {
        require(parts.size == 2) { "Rl expects 2 fields, got ${parts.size}" }
        return RowerPacket.ResistanceLevel(timestamp = timestamp, level = parts[1].toInt())
    }
}
