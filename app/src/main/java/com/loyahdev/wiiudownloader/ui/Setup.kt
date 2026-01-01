

package com.loyahdev.wiiudownloader.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.loyahdev.wiiudownloader.R

private const val PREFS_NAME = "wiiu_downloader_prefs"
private const val KEY_SETUP_COMPLETE = "setup_complete"

// Replace this later with your real website.
private const val GET_STARTED_URL = "https://www.google.com/search?q=WiiUDownloader+get+started"

/**
 * Setup flow:
 * 1) Welcome screen with app icon + Continue + Open Get Started Website
 * 2) Title Keys server screen with required input + validation
 *
 * Valid servers (variants accepted: with/without http(s)://, with/without trailing slash):
 * - http://vault.titlekeys.ovh/
 * - http://cldr.xyz/
 * - http://web.archive.org/web/20180512025652id_/http://wiiu.titlekeys.gq/
 */
@Composable
fun SetupScreen(
    onBack: () -> Unit,
    onFinished: () -> Unit,
    modifier: Modifier = Modifier
) {
    // 0 = welcome, 1 = titlekeys server
    var step by remember { mutableStateOf(0) }
    var serverInput by remember { mutableStateOf("") }
    var errorText by remember { mutableStateOf<String?>(null) }

    val context = LocalContext.current

    fun openUrl(url: String) {
        runCatching {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        }
    }

    fun normalizeForCompare(raw: String): String {
        var s = raw.trim().lowercase()
        if (s.startsWith("http://")) s = s.removePrefix("http://")
        if (s.startsWith("https://")) s = s.removePrefix("https://")
        while (s.endsWith("/")) s = s.dropLast(1)
        return s
    }

    fun isAllowedServer(raw: String): Pair<Boolean, String> {
        val norm = normalizeForCompare(raw)

        // Canonical compare targets (no scheme, no trailing slash)
        val allowed1 = "vault.titlekeys.ovh"
        val allowed2 = "cldr.xyz"
        val allowed3 = "web.archive.org/web/20180512025652id_/http://wiiu.titlekeys.gq"
        val allowed4 = "titlekeys.ovh"
        val ok = norm == allowed1 || norm == allowed2 || norm == allowed3 || norm == allowed4

        // Store canonical http URL with trailing slash
        val canonical = when (norm) {
            allowed1 -> "http://vault.titlekeys.ovh/"
            allowed2 -> "http://cldr.xyz/"
            allowed3 -> "http://web.archive.org/web/20180512025652id_/http://wiiu.titlekeys.gq/"
            allowed4 -> "http://titlekeys.ovh/"
            else -> ""
        }

        return ok to canonical
    }

    fun finishSetup() {
        val prefs = context.getSharedPreferences(PREFS_NAME, 0)
        prefs.edit()
            .putBoolean(KEY_SETUP_COMPLETE, true)
            .apply()
        onFinished()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Top
    ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Setup", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                TextButton(
                    onClick = {
                        if (step == 1) {
                            // Go back within setup flow
                            errorText = null
                            step = 0
                        } else {
                            // Exit setup screen
                            onBack()
                        }
                    }
                ) { Text("Back") }
            }

            Spacer(Modifier.height(16.dp))

            when (step) {
                0 -> {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        // App icon: android:roundIcon="@drawable/logo" -> same drawable
                        Image(
                            painter = painterResource(id = R.drawable.logo),
                            contentDescription = "App icon",
                            modifier = Modifier.size(110.dp)
                        )

                        Spacer(Modifier.height(14.dp))

                        Text(
                            "Welcome",
                            fontWeight = FontWeight.SemiBold,
                            style = MaterialTheme.typography.titleMedium
                        )

                        Spacer(Modifier.height(18.dp))

                        Button(
                            onClick = {
                                errorText = null
                                step = 1
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Continue")
                        }

                        Spacer(Modifier.height(10.dp))

                        OutlinedButton(
                            onClick = { openUrl(GET_STARTED_URL) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Open Get Started Website")
                        }
                    }
                }

                1 -> {
                    Text(
                        "Title Keys Server",
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.titleMedium
                    )

                    Spacer(Modifier.height(8.dp))

                    Text(
                        "Enter a link to a title keys server. Hint: use Google.",
                        style = MaterialTheme.typography.bodySmall
                    )

                    Spacer(Modifier.height(12.dp))

                    TextField(
                        value = serverInput,
                        onValueChange = {
                            serverInput = it
                            if (errorText != null) errorText = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("http://vault.titlekeys.ovh/") },
                        singleLine = true,
                        colors = TextFieldDefaults.colors()
                    )

                    if (errorText != null) {
                        Spacer(Modifier.height(8.dp))
                        Text(
                            errorText!!,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    Spacer(Modifier.height(14.dp))

                    Button(
                        onClick = {
                            val (ok, _) = isAllowedServer(serverInput)
                            if (!ok) {
                                errorText = "Incorrect link."
                                return@Button
                            }
                            finishSetup()
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Finish Setup")
                    }
                }
            }
        }
    }