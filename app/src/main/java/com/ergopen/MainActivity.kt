package com.ergopen

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import com.ergopen.ui.TelemetryScreen
import com.ergopen.ui.TelemetryViewModel

class MainActivity : ComponentActivity() {

    private val vm: TelemetryViewModel by viewModels()

    private val requestAudio = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            // Permission denied — UI will show error when user tries to connect
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestAudio.launch(Manifest.permission.RECORD_AUDIO)
        setContent {
            MaterialTheme {
                TelemetryScreen(vm)
            }
        }
    }
}
