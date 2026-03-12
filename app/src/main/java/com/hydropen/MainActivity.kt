package com.hydropen

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import com.hydropen.ui.TelemetryScreen
import com.hydropen.ui.TelemetryViewModel

class MainActivity : ComponentActivity() {

    private val vm: TelemetryViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                TelemetryScreen(vm)
            }
        }
    }
}
