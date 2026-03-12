package com.ergopen.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun TelemetryScreen(vm: TelemetryViewModel) {
    val state by vm.state.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(40.dp),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        // Status bar
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            val statusText = when {
                state.error != null -> "ERROR: ${state.error}"
                state.connected -> "CONNECTED  seq=${state.sequence}"
                else -> "DISCONNECTED"
            }
            val statusColor = when {
                state.error != null -> Color.Red
                state.connected -> Color.Green
                else -> Color.Gray
            }
            Text(statusText, color = statusColor, fontSize = 14.sp)
        }

        // Main metrics
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            MetricBox("WATTS", "%.0f".format(state.watts), Color(0xFFFFD700))
            MetricBox("RPM", "%.1f".format(state.rpm), Color.White)
            MetricBox("HZ", "${state.handleMm}", Color(0xFF00BFFF))
            MetricBox("REVS", "%.2f".format(state.revolutions), Color(0xFF90EE90))
        }

        // Raw signal monitor
        state.signalRaw?.let { signal ->
            Text(
                signal,
                color = Color(0xFF00FF88),
                fontSize = 14.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
        }

        // Stroke summary
        if (state.lastStrokeAvgWatts > 0f) {
            Text(
                "Last stroke avg: %.0f W".format(state.lastStrokeAvgWatts),
                color = Color.Gray,
                fontSize = 18.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
        }

        // Controls
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Button(onClick = { vm.connect(fake = false) }) {
                Text("Connect Rower")
            }
            Button(
                onClick = { vm.connect(fake = true) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF444444))
            ) {
                Text("Fake Data")
            }
            if (state.connected) {
                Button(
                    onClick = { vm.disconnect() },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF880000))
                ) {
                    Text("Disconnect")
                }
            }
        }
    }
}

@Composable
fun MetricBox(label: String, value: String, valueColor: Color = Color.White) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = Color.Gray, fontSize = 16.sp, fontWeight = FontWeight.Medium)
        Spacer(Modifier.height(8.dp))
        Text(value, color = valueColor, fontSize = 56.sp, fontWeight = FontWeight.Bold)
    }
}
