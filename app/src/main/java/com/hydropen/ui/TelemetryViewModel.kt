package com.hydropen.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hydropen.sensor.FakeSensor
import com.hydropen.sensor.ErgSerial
import com.hydropen.sensor.RowerPacket
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch

data class TelemetryState(
    val rpm: Float = 0f,
    val watts: Float = 0f,
    val handleMm: Int = 0,
    val revolutions: Float = 0f,
    val lastStrokeAvgWatts: Float = 0f,
    val sequence: Int = 0,
    val connected: Boolean = false,
    val error: String? = null
)

class TelemetryViewModel : ViewModel() {

    private val _state = MutableStateFlow(TelemetryState())
    val state: StateFlow<TelemetryState> = _state

    private var job: Job? = null

    fun connect(fake: Boolean = false) {
        job?.cancel()
        _state.value = TelemetryState(connected = false)

        val source = if (fake) FakeSensor.packets() else ErgSerial.packets()

        job = viewModelScope.launch {
            source.catch { e ->
                _state.value = _state.value.copy(connected = false, error = e.message)
            }.collect { packet ->
                when (packet) {
                    is RowerPacket.Instantaneous -> _state.value = _state.value.copy(
                        connected = true,
                        error = null,
                        rpm = packet.rpm,
                        watts = packet.watts,
                        handleMm = packet.handleMm,
                        revolutions = packet.revolutions,
                        sequence = packet.sequence
                    )
                    is RowerPacket.Stroke -> _state.value = _state.value.copy(
                        lastStrokeAvgWatts = packet.averageWatts
                    )
                    else -> Unit
                }
            }
        }
    }

    fun disconnect() {
        job?.cancel()
        job = null
        _state.value = TelemetryState()
    }
}
