package com.ergopen.sensor

sealed class RowerPacket {

    // Di <rpm5> <revolutions100> <watts10> <handleMM> <sequence>
    data class Instantaneous(
        val timestamp: Long,
        val rpm: Float,         // raw rpm5 / 5.0
        val revolutions: Float, // raw revolutions100 / 100.0
        val watts: Float,       // raw watts10 / 10.0
        val handleMm: Int,
        val sequence: Int
    ) : RowerPacket()

    // Ds <startPosition> <endPosition> <driveRev10> <recoveryRev10> <avgWatts10>
    //    <lastPacketRecoveryEndIndex> <driveEndIndex> <sequence>
    data class Stroke(
        val timestamp: Long,
        val startPosition: Int,
        val endPosition: Int,
        val driveRevolutions: Float,    // raw driveStrokeRevolution10 / 10.0
        val recoveryRevolutions: Float, // raw recoveryStrokeRevolution10 / 10.0
        val averageWatts: Float,        // raw averageWatts10 / 10.0
        val lastPacketRecoveryEndIndex: Int,
        val driveEndIndex: Int,
        val sequence: Int
    ) : RowerPacket()

    // Rl <resistanceSetting>
    data class ResistanceLevel(
        val timestamp: Long,
        val level: Int
    ) : RowerPacket()

    data class Version(val timestamp: Long, val version: String) : RowerPacket()
    data class SerialNumber(val timestamp: Long, val serial: String) : RowerPacket()
    data class Health(val timestamp: Long, val raw: String) : RowerPacket()
    data class Unknown(val timestamp: Long, val raw: String) : RowerPacket()
}
