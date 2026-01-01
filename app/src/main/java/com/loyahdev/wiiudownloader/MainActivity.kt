package com.loyahdev.wiiudownloader
// WiiUDownloaderLayout.kt
// Jetpack Compose (Material3) layout-only remake of the screenshot UI.
// Filters/queue don’t do anything; everything is placeholder.


import android.annotation.SuppressLint
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.ui.input.pointer.pointerInput
// --- Pointer/gesture imports for scroll indicator ---
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.PointerInputChange
import androidx.compose.ui.input.pointer.consumeAllChanges
import androidx.compose.ui.platform.LocalDensity
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.ui.platform.LocalContext
import org.json.JSONArray
import java.nio.charset.StandardCharsets
import android.util.Log
import com.loyahdev.wiiudownloader.ui.SetupScreen

enum class AppPage {
    BROWSE,
    QUEUE,
    DOWNLOADS,
    SETUP
}

private const val PREFS_NAME = "wiiu_downloader_prefs"
private const val KEY_SETUP_COMPLETE = "setup_complete"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    WiiUDownloaderLayout()
                }
            }
        }
    }
}

data class TitleRow(
    val type: String,
    val titleId: String,
    val region: String,
    val name: String,
)

@SuppressLint("UnusedBoxWithConstraintsScope")
@Composable
fun WiiUDownloaderLayout() {
    val sidebarItems = remember { listOf<String>() } // empty like the screenshot

    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS_NAME, 0) }
    var setupComplete by remember { mutableStateOf(prefs.getBoolean(KEY_SETUP_COMPLETE, false)) }

    // Load + parse titles.json from assets. Supports either:
    // 1) A proper JSON array: [ { ... }, { ... } ]
    // 2) A file containing multiple objects separated by commas/newlines (no surrounding [ ]).
    val titlesState by produceState<Pair<List<TitleRow>, String?>>(initialValue = Pair(emptyList(), null)) {
        val result = runCatching {
            val raw = context.assets.open("titles.json").use { input ->
                val bytes = input.readBytes()
                String(bytes, StandardCharsets.UTF_8)
            }.trim()

            val normalized = when {
                raw.startsWith("[") -> raw
                raw.isEmpty() -> "[]"
                else -> {
                    // Attempt to wrap loose objects into an array.
                    // Remove trailing commas so JSON stays valid.
                    val cleaned = raw.replace(Regex(",\\s*$"), "")
                    "[\n$cleaned\n]"
                }
            }

            val arr = JSONArray(normalized)
            buildList {
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val titleId = obj.optString("titleID").trim()
                    val name = obj.optString("name").trim()
                    val region = obj.optString("region").trim()
                    val type = obj.optString("type").trim()
                    if (titleId.isNotBlank() && name.isNotBlank()) {
                        add(
                            TitleRow(
                                type = type,
                                titleId = titleId,
                                region = region,
                                name = name
                            )
                        )
                    }
                }
            }
        }

        value = result.fold(
            onSuccess = { Pair(it, null) },
            onFailure = { e ->
                Log.e("WiiUDownloader", "Failed to load titles.json", e)
                Pair(emptyList(), "titles.json parse error: ${e.message}")
            }
        )
    }

    val rows: List<TitleRow> = titlesState.first
    val loadError: String? = titlesState.second

    var tab by remember { mutableIntStateOf(0) }
    val tabLabels = listOf("Application", "System", "DLC", "Patch", "Demo", "All")

    var search by remember { mutableStateOf("") }

    var page by remember { mutableStateOf(if (setupComplete) AppPage.BROWSE else AppPage.SETUP) }

    LaunchedEffect(setupComplete) {
        if (!setupComplete) page = AppPage.SETUP
    }

    // Bottom bar toggles (layout-only)
    var decryptContents by remember { mutableStateOf(true) }
    var deleteAfterDecrypt by remember { mutableStateOf(false) }
    var regionEurope by remember { mutableStateOf(false) }
    var regionUsa by remember { mutableStateOf(true) }
    var regionJapan by remember { mutableStateOf(false) }

    val selectedIds = remember { mutableStateSetOf<String>() }
    val downloadingIds = remember { mutableStateSetOf<String>() }
    var showQueueLimitDialog by remember { mutableStateOf(false) }
    var showDownloadLimitDialog by remember { mutableStateOf(false) }
    var showSetupDialog by remember { mutableStateOf(false) }

    val filteredRows = rows.filter { row ->
        val regionMatch = when (row.region) {
            "USA" -> regionUsa
            "EUR" -> regionEurope
            "JPN" -> regionJapan
            else -> true
        }

        val typeMatch = when (tab) {
            0 -> row.type == "Application"
            1 -> row.type == "System Application"
            2 -> row.type == "DLC"
            3 -> row.type == "Patch"
            4 -> row.type == "Demo"
            else -> true
        }

        val q = search.trim()
        val searchMatch = if (q.isEmpty()) true
        else row.name.contains(q, ignoreCase = true) || row.titleId.contains(q, ignoreCase = true)

        regionMatch && typeMatch && searchMatch
    }

    Scaffold(
        bottomBar = {
            // Hide region filters during Setup (and until setup is completed)
            if (setupComplete && page != AppPage.SETUP) {
                BottomBar(
                    decryptContents = decryptContents,
                    onDecryptContentsChange = { decryptContents = it },
                    deleteAfterDecrypt = deleteAfterDecrypt,
                    onDeleteAfterDecryptChange = { deleteAfterDecrypt = it },
                    regionEurope = regionEurope,
                    onRegionEuropeChange = { regionEurope = it },
                    regionUsa = regionUsa,
                    onRegionUsaChange = { regionUsa = it },
                    regionJapan = regionJapan,
                    onRegionJapanChange = { regionJapan = it },
                )
            }
        }
    ) { padding ->
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (showQueueLimitDialog) {
                AlertDialog(
                    onDismissRequest = { showQueueLimitDialog = false },
                    confirmButton = {
                        TextButton(onClick = { showQueueLimitDialog = false }) {
                            Text("OK")
                        }
                    },
                    title = { Text("Queue limit") },
                    text = { Text("Limited to 3 to improve performance") }
                )
            }
            if (showDownloadLimitDialog) {
                AlertDialog(
                    onDismissRequest = { showDownloadLimitDialog = false },
                    confirmButton = {
                        TextButton(onClick = { showDownloadLimitDialog = false }) {
                            Text("OK")
                        }
                    },
                    title = { Text("Download limit") },
                    text = { Text("Only 1 download at a time") }
                )
            }
            /*if (showSetupDialog) {
                AlertDialog(
                    onDismissRequest = { showSetupDialog = false },
                    confirmButton = {
                        TextButton(
                            onClick = {
                                showSetupDialog = false
                                page = AppPage.SETUP
                            }
                        ) { Text("Open Setup") }
                    },
                    dismissButton = {
                        TextButton(onClick = { showSetupDialog = false }) { Text("Cancel") }
                    },
                    title = { Text("Setup") },
                    text = { Text("Open the setup screen.") }
                )
            }*/
            Column(Modifier.fillMaxSize()) {
                // Simple header (no AppBar)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("WiiUDownloader Android", fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(2.dp))
                        Text(
                            "Made by loyahdev",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(Modifier.weight(1f))
                    if (setupComplete) {
                        TextButton(
                            onClick = { page = AppPage.BROWSE },
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text("Browse")
                        }
                        Spacer(Modifier.width(8.dp))
                        TextButton(
                            onClick = { page = AppPage.QUEUE },
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text("Queue")
                        }
                        Spacer(Modifier.width(8.dp))
                        TextButton(
                            onClick = { page = AppPage.DOWNLOADS },
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text("Downloads")
                        }
                    } else {
                        TextButton(
                            onClick = { page = AppPage.SETUP },
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text("Setup")
                        }
                    }
                }

                when (page) {
                    AppPage.BROWSE -> {
                        if (rows.isEmpty()) {
                            Surface(
                                tonalElevation = 1.dp,
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(12.dp)
                            ) {
                                Column(
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .padding(16.dp),
                                    verticalArrangement = Arrangement.Center,
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Text(
                                        text = "No titles loaded",
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Spacer(Modifier.height(8.dp))
                                    Text(
                                        text = loadError
                                            ?: "Make sure titles.json is in app/src/main/assets and is valid JSON (array or comma-separated objects).",
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }
                            }
                        } else {
                            MainPanel(
                                tab = tab,
                                tabLabels = tabLabels,
                                onTabChange = { tab = it },
                                search = search,
                                onSearchChange = { search = it },
                                rows = filteredRows,
                                selectedIds = selectedIds,
                                onToggleSelect = { titleId, isChecked ->
                                    if (isChecked) {
                                        // Allow up to 3 queued items
                                        if (!selectedIds.contains(titleId) && selectedIds.size >= 3) {
                                            showQueueLimitDialog = true
                                        } else {
                                            selectedIds.add(titleId)
                                        }
                                    } else {
                                        selectedIds.remove(titleId)
                                    }
                                },
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(12.dp)
                            )
                        }
                    }
                    AppPage.QUEUE -> {
                        QueuePage(
                            rows = rows.filter { selectedIds.contains(it.titleId) },
                            selectedIds = selectedIds,
                            canStartDownload = downloadingIds.isEmpty(),
                            onDownloadBlocked = { showDownloadLimitDialog = true },
                            onStartDownload = { row ->
                                // Start this specific queued item, then go to Downloads page
                                downloadingIds.add(row.titleId)
                                selectedIds.remove(row.titleId)
                                page = AppPage.DOWNLOADS

                                // Hook: later you will start your python worker/bridge here.
                            },
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(12.dp)
                        )
                    }
                    AppPage.DOWNLOADS -> {
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(12.dp)
                        ) {
                            /*Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("Downloads", fontWeight = FontWeight.SemiBold)
                                Spacer(Modifier.weight(1f))
                                OutlinedButton(onClick = { showSetupDialog = true }) {
                                    Text("Setup")
                                }
                            }

                            Spacer(Modifier.height(12.dp))*/

                            DownloadsPage(
                                games = rows.filter { downloadingIds.contains(it.titleId) },
                                onCancelDownload = { game ->
                                    downloadingIds.remove(game.titleId)
                                },
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                    }
                    AppPage.SETUP -> {
                        SetupScreen(
                            onBack = {
                                // If setup isn't done yet, don't allow leaving setup.
                                if (setupComplete) page = AppPage.DOWNLOADS else page = AppPage.SETUP
                            },
                            onFinished = {
                                // Re-read prefs and unlock the app
                                setupComplete = prefs.getBoolean(KEY_SETUP_COMPLETE, false)
                                page = AppPage.BROWSE
                            },
                            modifier = Modifier.fillMaxSize()
                        )
                    }
                }
            }
        }
    }
}


@Composable
private fun MainPanel(
    tab: Int,
    tabLabels: List<String>,
    onTabChange: (Int) -> Unit,
    search: String,
    onSearchChange: (String) -> Unit,
    rows: List<TitleRow>,
    selectedIds: MutableSet<String>,
    onToggleSelect: (titleId: String, isChecked: Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        tonalElevation = 1.dp,
        shape = RoundedCornerShape(10.dp),
        modifier = modifier
    ) {
        Column(Modifier.fillMaxSize().padding(12.dp)) {
            // Tabs row + Search
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.heightIn(min = 40.dp)
            ) {
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .horizontalScroll(rememberScrollState()),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row {
                        tabLabels.forEachIndexed { index, label ->
                            TextButton(
                                onClick = { onTabChange(index) },
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    label,
                                    fontWeight = if (tab == index) FontWeight.SemiBold else FontWeight.Normal
                                )
                            }
                        }
                    }
                }

                Spacer(Modifier.width(12.dp))

                OutlinedTextField(
                    value = search,
                    onValueChange = onSearchChange,
                    singleLine = true,
                    placeholder = { Text("Search") },
                    leadingIcon = { Icon(Icons.Filled.Search, contentDescription = "Search") },
                    modifier = Modifier
                        .widthIn(min = 160.dp, max = 320.dp)
                        .heightIn(min = 40.dp)
                )
            }

            Spacer(Modifier.height(8.dp))

            GameList(
                rows = rows,
                selectedIds = selectedIds,
                selectable = true,
                onToggleSelect = onToggleSelect,
                modifier = Modifier.weight(1f)
            )

            Spacer(Modifier.height(12.dp))
        }
    }
}



// Table, TableRow, HeaderCell composables deleted (reset to downloader pattern)

@Composable
private fun BottomBar(
    decryptContents: Boolean,
    onDecryptContentsChange: (Boolean) -> Unit,
    deleteAfterDecrypt: Boolean,
    onDeleteAfterDecryptChange: (Boolean) -> Unit,
    regionEurope: Boolean,
    onRegionEuropeChange: (Boolean) -> Unit,
    regionUsa: Boolean,
    onRegionUsaChange: (Boolean) -> Unit,
    regionJapan: Boolean,
    onRegionJapanChange: (Boolean) -> Unit,
) {
    Surface(tonalElevation = 3.dp) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 4.dp)
        ) {

            // Region filters (second row)
            val scrollState = rememberScrollState()

            Row(
                modifier = Modifier.horizontalScroll(scrollState),
                verticalAlignment = Alignment.CenterVertically
            ) {
                /*Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = decryptContents, onCheckedChange = onDecryptContentsChange)
                    Text("Decrypt contents")
                }

                Spacer(Modifier.width(12.dp))

                Text("|")*/

                Spacer(Modifier.width(12.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = regionEurope, onCheckedChange = onRegionEuropeChange)
                    Text("Europe")
                }
                Spacer(Modifier.width(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = regionUsa, onCheckedChange = onRegionUsaChange)
                    Text("USA")
                }
                Spacer(Modifier.width(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = regionJapan, onCheckedChange = onRegionJapanChange)
                    Text("Japan")
                }
            }

            Spacer(Modifier.height(4.dp))

            if (scrollState.maxValue > 0) {
                LinearProgressIndicator(
                    progress = if (scrollState.maxValue == 0) 0f
                    else scrollState.value.toFloat() / scrollState.maxValue.toFloat(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(2.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
                    trackColor = MaterialTheme.colorScheme.outlineVariant
                )
            }
        }
    }
}
@Composable
private fun QueuePage(
    rows: List<TitleRow>,
    selectedIds: MutableSet<String>,
    canStartDownload: Boolean,
    onDownloadBlocked: () -> Unit,
    onStartDownload: (TitleRow) -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        tonalElevation = 1.dp,
        shape = RoundedCornerShape(10.dp),
        modifier = modifier
    ) {
        Column(Modifier.fillMaxSize().padding(12.dp)) {
            Text("Queue", fontWeight = FontWeight.SemiBold)

            Spacer(Modifier.height(12.dp))

            GameList(
                rows = rows,
                selectedIds = selectedIds,
                selectable = false,
                onRemove = { row ->
                    selectedIds.remove(row.titleId)
                },
                onDownload = { row ->
                    if (!canStartDownload) {
                        onDownloadBlocked()
                        return@GameList
                    }
                    onStartDownload(row)
                },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

// --- Downloader Pattern UI ---
@Composable
private fun GameList(
    rows: List<TitleRow>,
    selectedIds: MutableSet<String>,
    selectable: Boolean,
    onToggleSelect: ((titleId: String, isChecked: Boolean) -> Unit)? = null,
    onRemove: ((TitleRow) -> Unit)? = null,
    onDownload: ((TitleRow) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val density = LocalDensity.current

    Box(modifier = modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize()
        ) {
            items(
                items = rows,
                key = { r: TitleRow -> r.titleId }
            ) { row: TitleRow ->
                GameRow(
                    row = row,
                    checked = selectedIds.contains(row.titleId),
                    selectable = selectable,
                    onCheckedChange = { isChecked ->
                        if (onToggleSelect != null) {
                            onToggleSelect(row.titleId, isChecked)
                        } else {
                            if (isChecked) selectedIds.add(row.titleId)
                            else selectedIds.remove(row.titleId)
                        }
                    },
                    onRemove = onRemove,
                    onDownload = onDownload
                )
                HorizontalDivider(thickness = 0.5.dp)
            }
        }

        // Simple scroll indicator (right side)
        if (rows.size > 6) {
            BoxWithConstraints(
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .fillMaxHeight()
                    .width(10.dp)
                    .padding(vertical = 8.dp)
                    .background(
                        MaterialTheme.colorScheme.outlineVariant,
                        RoundedCornerShape(999.dp)
                    )
            ) {
                val trackHeight = maxHeight
                val trackHeightPx = with(LocalDensity.current) { trackHeight.toPx() }

                val visibleCount = listState.layoutInfo.visibleItemsInfo.size.coerceAtLeast(1)
                val total = rows.size.coerceAtLeast(1)
                val maxStart = (total - visibleCount).coerceAtLeast(1)

                // Gesture layer (tap/drag on the track)
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .pointerInput(rows.size, trackHeightPx) {
                            detectDragGestures(
                                onDragStart = { start: Offset ->
                                    val fraction = (start.y / trackHeightPx).coerceIn(0f, 1f)
                                    val targetIndex = (fraction * maxStart.toFloat()).roundToInt()
                                    scope.launch { listState.scrollToItem(targetIndex) }
                                },
                                onDrag = { change: PointerInputChange, _: Offset ->
                                    change.consumeAllChanges()
                                    val fraction = (change.position.y / trackHeightPx).coerceIn(0f, 1f)
                                    val targetIndex = (fraction * maxStart.toFloat()).roundToInt()
                                    scope.launch { listState.scrollToItem(targetIndex) }
                                }
                            )
                        }
                )

                // Thumb drawing (same logic as before)
                val firstVisible = listState.firstVisibleItemIndex

                val thumbFraction = (visibleCount.toFloat() / total.toFloat()).coerceIn(0.10f, 1f)
                val thumbHeight = trackHeight * thumbFraction

                val startFraction = (firstVisible.toFloat() / maxStart.toFloat()).coerceIn(0f, 1f)
                val yOffset = (trackHeight - thumbHeight) * startFraction

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(thumbHeight)
                        .offset(y = yOffset)
                        .background(
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.55f),
                            RoundedCornerShape(999.dp)
                        )
                )
            }
        }
    }
}

@Composable
private fun GameRow(
    row: TitleRow,
    checked: Boolean,
    selectable: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    onRemove: ((TitleRow) -> Unit)? = null,
    onDownload: ((TitleRow) -> Unit)? = null
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (selectable) {
            Checkbox(
                checked = checked,
                onCheckedChange = onCheckedChange
            )
            Spacer(Modifier.width(12.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(row.name, fontWeight = FontWeight.SemiBold, maxLines = 2)
            Spacer(Modifier.height(2.dp))
            Text(
                "${row.type} • ${row.region} • ${row.titleId}",
                style = MaterialTheme.typography.bodySmall
            )
        }

        if (!selectable) {
            if (onDownload != null) {
                Spacer(Modifier.width(8.dp))
                IconButton(onClick = { onDownload(row) }) {
                    Icon(
                        imageVector = Icons.Filled.ArrowDownward,
                        contentDescription = "Download"
                    )
                }
            }
            if (onRemove != null) {
                Spacer(Modifier.width(8.dp))
                IconButton(onClick = { onRemove(row) }) {
                    Text("✕", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}