package com.loyahdev.wiiudownloader

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.*
import java.io.File
import android.content.*
import android.net.Uri
import android.os.*
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import androidx.compose.material.icons.filled.Folder
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.FileInputStream
import android.provider.DocumentsContract
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import android.app.*
import android.content.BroadcastReceiver
import android.content.IntentFilter
import android.os.Build
import kotlin.math.roundToInt

/**
 * Detailed UI state for a single download.
 */
data class DownloadUiState(
    val isRunning: Boolean = false,
    val progress: Float = 0f,
    val status: String = "Waiting…",
    val currentFile: Int = 0,
    val totalFiles: Int = 0,
    val downloadedMB: Float = 0f,
    val totalMB: Float = 0f,
    val currentSpeed: Float = 0f,
    val timeRemaining: String = "",
    val error: String? = null,
    val isComplete: Boolean = false,
    val outputPath: String? = null,
    val phase: DownloadPhase = DownloadPhase.IDLE,
    val isDecrypting: Boolean = false,
    val isExtracting: Boolean = false,
    val decryptionProgress: Float = 0f,
    val extractionProgress: Float = 0f
)


// ViewModel for downloads
class DownloadsViewModel : ViewModel() {
    val downloadStates = mutableStateMapOf<String, DownloadUiState>()
    val activeDownloads = mutableStateMapOf<String, Boolean>()
    var outputDirUri by mutableStateOf<Uri?>(null)
}

// Bridge classes
class ProgressBridge(
    private val onUpdate: (Int, String, Int, Int, Float, Float) -> Unit,
    private val onPhaseChange: (DownloadPhase) -> Unit,
    private val onDecryptionProgress: (Float, String) -> Unit,
    private val onExtractionProgress: (Float, String) -> Unit
) {
    private val handler = Handler(Looper.getMainLooper())

    fun update(percent: Int, message: String, currentFile: Int, totalFiles: Int, downloadedMB: Float, totalMB: Float) {
        handler.post {
            onUpdate(percent, message, currentFile, totalFiles, downloadedMB, totalMB)
        }
    }

    fun updatePhase(phase: DownloadPhase) {
        handler.post {
            onPhaseChange(phase)
        }
    }

    fun updateDecryptionProgress(percent: Float, message: String) {
        handler.post {
            onDecryptionProgress(percent, message)
        }
    }

    fun updateExtractionProgress(percent: Float, message: String) {
        handler.post {
            onExtractionProgress(percent, message)
        }
    }
}

class CancelToken {
    @Volatile private var cancelled: Boolean = false

    fun cancel() { cancelled = true }
    fun reset() { cancelled = false }
    fun is_cancelled(): Boolean = cancelled
}

// Helper functions
private fun copyLocalFileToSafDir(
    context: Context,
    treeUri: Uri,
    parentDirDocUri: Uri,
    displayName: String,
    mimeType: String,
    sourceFile: File
): Uri {
    val created = DocumentsContract.createDocument(
        context.contentResolver,
        parentDirDocUri,
        mimeType,
        displayName
    ) ?: throw IllegalStateException("Failed to create destination file")

    val createdDocId = DocumentsContract.getDocumentId(created)
    val createdInTree = DocumentsContract.buildDocumentUriUsingTree(treeUri, createdDocId)

    context.contentResolver.openOutputStream(createdInTree)?.use { out ->
        FileInputStream(sourceFile).use { input ->
            val buffer = ByteArray(1024 * 64)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                out.write(buffer, 0, read)
            }
            out.flush()
        }
    } ?: throw IllegalStateException("Failed to open SAF output stream")

    return createdInTree
}

private fun createSafDirectory(
    context: Context,
    treeUri: Uri,
    parentDirDocUri: Uri,
    dirName: String
): Uri {
    val created = DocumentsContract.createDocument(
        context.contentResolver,
        parentDirDocUri,
        DocumentsContract.Document.MIME_TYPE_DIR,
        dirName
    ) ?: throw IllegalStateException("Failed to create directory: $dirName")

    val createdDocId = DocumentsContract.getDocumentId(created)
    return DocumentsContract.buildDocumentUriUsingTree(treeUri, createdDocId)
}

private fun copyLocalDirToSafDir(
    context: Context,
    destParentTreeUri: Uri,
    sourceDir: File
): Uri {
    if (!sourceDir.exists() || !sourceDir.isDirectory) {
        throw IllegalArgumentException("sourceDir is not a directory: ${sourceDir.absolutePath}")
    }

    val destParentDocUri = if (DocumentsContract.isTreeUri(destParentTreeUri)) {
        DocumentsContract.buildDocumentUriUsingTree(
            destParentTreeUri,
            DocumentsContract.getTreeDocumentId(destParentTreeUri)
        )
    } else {
        destParentTreeUri
    }

    val destRootDirUri = createSafDirectory(
        context = context,
        treeUri = destParentTreeUri,
        parentDirDocUri = destParentDocUri,
        dirName = sourceDir.name
    )

    fun recurse(src: File, destDirDocUri: Uri) {
        val children = src.listFiles() ?: return
        for (child in children) {
            if (child.isDirectory) {
                val childDestDirUri = createSafDirectory(
                    context = context,
                    treeUri = destParentTreeUri,
                    parentDirDocUri = destDirDocUri,
                    dirName = child.name
                )
                recurse(child, childDestDirUri)
            } else {
                copyLocalFileToSafDir(
                    context = context,
                    treeUri = destParentTreeUri,
                    parentDirDocUri = destDirDocUri,
                    displayName = child.name,
                    mimeType = "application/octet-stream",
                    sourceFile = child
                )
            }
        }
    }

    recurse(sourceDir, destRootDirUri)
    return destRootDirUri
}

// Download service constants
object DownloadServiceConstants {
    const val ACTION_START = "com.loyahdev.wiiudownloader.action.START"
    const val ACTION_CANCEL = "com.loyahdev.wiiudownloader.action.CANCEL"
    const val ACTION_PROGRESS = "com.loyahdev.wiiudownloader.action.PROGRESS"

    const val EXTRA_TITLE = "extra_title"
    const val EXTRA_WORK_DIR = "extra_work_dir"
    const val EXTRA_OUTPUT_TREE = "extra_output_tree"
    const val EXTRA_DELETE_AFTER_COPY = "extra_delete_after_copy"

    const val EXTRA_STATUS = "extra_status"
    const val EXTRA_MSG = "extra_msg"
    const val EXTRA_CUR = "extra_cur"
    const val EXTRA_TOTAL = "extra_total"
    const val EXTRA_RUNNING = "extra_running"
    const val EXTRA_RESULT = "extra_result"
    const val EXTRA_DOWNLOADED_MB = "extra_downloaded_mb"
    const val EXTRA_TOTAL_MB = "extra_total_mb"
    const val EXTRA_PHASE = "extra_phase"
    const val EXTRA_DECRYPTION_PROGRESS = "extra_decryption_progress"
    const val EXTRA_EXTRACTION_PROGRESS = "extra_extraction_progress"
    const val EXTRA_IS_DECRYPTING = "extra_is_decrypting"
    const val EXTRA_IS_EXTRACTING = "extra_is_extracting"
}

/**
 * Downloads page with detailed progress tracking.
 */
@Composable
fun DownloadsPage(
    games: List<TitleRow>,
    modifier: Modifier = Modifier,
    onCancelDownload: (TitleRow) -> Unit = {}
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val viewModel: DownloadsViewModel = viewModel()

    // Broadcast receiver for download updates
    DisposableEffect(Unit) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action != DownloadServiceConstants.ACTION_PROGRESS) return

                val titleId = intent.getStringExtra(DownloadServiceConstants.EXTRA_TITLE) ?: return
                val status = intent.getStringExtra(DownloadServiceConstants.EXTRA_STATUS) ?: ""
                val msg = intent.getStringExtra(DownloadServiceConstants.EXTRA_MSG)
                val currentFile = intent.getIntExtra(DownloadServiceConstants.EXTRA_CUR, 0)
                val totalFiles = intent.getIntExtra(DownloadServiceConstants.EXTRA_TOTAL, 0)
                val isRunning = intent.getBooleanExtra(DownloadServiceConstants.EXTRA_RUNNING, false)
                val resultText = intent.getStringExtra(DownloadServiceConstants.EXTRA_RESULT)
                val downloadedMB = intent.getFloatExtra(DownloadServiceConstants.EXTRA_DOWNLOADED_MB, 0f)
                val totalMB = intent.getFloatExtra(DownloadServiceConstants.EXTRA_TOTAL_MB, 0f)
                val phaseStr = intent.getStringExtra(DownloadServiceConstants.EXTRA_PHASE)
                val decryptionProgress = intent.getFloatExtra(DownloadServiceConstants.EXTRA_DECRYPTION_PROGRESS, 0f)
                val extractionProgress = intent.getFloatExtra(DownloadServiceConstants.EXTRA_EXTRACTION_PROGRESS, 0f)
                val isDecrypting = intent.getBooleanExtra(DownloadServiceConstants.EXTRA_IS_DECRYPTING, false)
                val isExtracting = intent.getBooleanExtra(DownloadServiceConstants.EXTRA_IS_EXTRACTING, false)

                val phase = try {
                    DownloadPhase.valueOf(phaseStr ?: "IDLE")
                } catch (e: Exception) {
                    DownloadPhase.IDLE
                }

                val progress = if (totalFiles > 0) {
                    currentFile.toFloat() / totalFiles.toFloat()
                } else if (isDecrypting) {
                    decryptionProgress / 100f
                } else if (isExtracting) {
                    extractionProgress / 100f
                } else {
                    0f
                }

                viewModel.downloadStates[titleId] = DownloadUiState(
                    isRunning = isRunning,
                    progress = progress,
                    status = msg ?: status,
                    currentFile = currentFile,
                    totalFiles = totalFiles,
                    downloadedMB = downloadedMB,
                    totalMB = totalMB,
                    error = if (!isRunning && msg?.contains("error", ignoreCase = true) == true) msg else null,
                    isComplete = !isRunning && resultText != null,
                    outputPath = resultText,
                    phase = phase,
                    isDecrypting = isDecrypting,
                    isExtracting = isExtracting,
                    decryptionProgress = decryptionProgress / 100f,
                    extractionProgress = extractionProgress / 100f
                )

                viewModel.activeDownloads[titleId] = isRunning
            }
        }

        val filter = IntentFilter(DownloadServiceConstants.ACTION_PROGRESS)
        if (Build.VERSION.SDK_INT >= 33) {
            context.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            context.registerReceiver(receiver, filter)
        }

        onDispose {
            try {
                context.unregisterReceiver(receiver)
            } catch (_: Throwable) {}
        }
    }

    // Folder picker launcher
    val folderPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri: Uri? ->
        if (uri == null) {
            return@rememberLauncherForActivityResult
        }

        val flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        try {
            context.contentResolver.takePersistableUriPermission(uri, flags)
            viewModel.outputDirUri = uri
        } catch (e: SecurityException) {
            viewModel.outputDirUri = uri
        }
    }

    // Function to start a real download using the service
    fun startDownload(game: TitleRow) {
        if (viewModel.outputDirUri == null) {
            folderPickerLauncher.launch(null)
            return
        }

        if (viewModel.activeDownloads.containsKey(game.titleId)) return

        viewModel.activeDownloads[game.titleId] = true
        viewModel.downloadStates[game.titleId] = DownloadUiState(
            isRunning = true,
            progress = 0f,
            status = "Starting download...",
            phase = DownloadPhase.INITIALIZING
        )

        // Initialize Python if needed
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context))
        }

        // Create work directory
        val workDir = File(context.getExternalFilesDir(null), "downloads/${game.titleId}")
        workDir.mkdirs()

        // Start the download service
        val intent = Intent(context, DownloadService::class.java).apply {
            action = DownloadServiceConstants.ACTION_START
            putExtra(DownloadServiceConstants.EXTRA_TITLE, game.titleId)
            putExtra(DownloadServiceConstants.EXTRA_WORK_DIR, workDir.absolutePath)
            putExtra(DownloadServiceConstants.EXTRA_OUTPUT_TREE, viewModel.outputDirUri.toString())
            putExtra(DownloadServiceConstants.EXTRA_DELETE_AFTER_COPY, true)
        }

        if (Build.VERSION.SDK_INT >= 26) {
            ContextCompat.startForegroundService(context, intent)
        } else {
            context.startService(intent)
        }
    }

    // Function to cancel download
    fun cancelDownload(gameId: String) {
        viewModel.activeDownloads.remove(gameId)
        viewModel.downloadStates[gameId]?.let { state ->
            viewModel.downloadStates[gameId] = state.copy(
                isRunning = false,
                status = "Cancelling...",
                error = "Download cancelled by user"
            )
        }

        val intent = Intent(context, DownloadService::class.java).apply {
            action = DownloadServiceConstants.ACTION_CANCEL
            putExtra(DownloadServiceConstants.EXTRA_TITLE, gameId)
        }
        context.startService(intent)
    }

    // Function to clear work directory
    fun clearWorkDirectory() {
        scope.launch {
            try {
                val workDir = File(context.getExternalFilesDir(null), "downloads")
                val deleted = withContext(Dispatchers.IO) {
                    if (workDir.exists()) {
                        workDir.deleteRecursively()
                    } else {
                        false
                    }
                }
            } catch (t: Throwable) {
                // Log error if needed
            }
        }
    }

    // Helper function to get status color based on phase
    @Composable
    fun getStatusColor(phase: DownloadPhase): androidx.compose.ui.graphics.Color {
        return when (phase) {
            DownloadPhase.DOWNLOADING_CONTENT -> MaterialTheme.colorScheme.primary
            DownloadPhase.DECRYPTING -> MaterialTheme.colorScheme.secondary
            DownloadPhase.EXTRACTING -> MaterialTheme.colorScheme.tertiary
            DownloadPhase.COMPLETE -> MaterialTheme.colorScheme.primary
            DownloadPhase.ERROR -> MaterialTheme.colorScheme.error
            else -> MaterialTheme.colorScheme.onSurfaceVariant
        }
    }

    // Helper function to get phase icon text
    fun getPhaseIcon(phase: DownloadPhase): String {
        return when (phase) {
            DownloadPhase.INITIALIZING -> "⚙"
            DownloadPhase.DOWNLOADING_METADATA -> "📋"
            DownloadPhase.DOWNLOADING_CONTENT -> "⬇"
            DownloadPhase.DECRYPTING -> "🔓"
            DownloadPhase.EXTRACTING -> "📦"
            DownloadPhase.FINALIZING -> "⏳"
            DownloadPhase.COMPLETE -> "✓"
            DownloadPhase.ERROR -> "✗"
            else -> ""
        }
    }

    Surface(modifier = modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
            // Output folder selection
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp)
                ) {
                    Text(
                        text = "Output Folder",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )

                    Spacer(Modifier.height(8.dp))

                    if (viewModel.outputDirUri == null) {
                        Text(
                            text = "No folder selected",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    } else {
                        Text(
                            text = "Folder selected ✓",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    Spacer(Modifier.height(8.dp))

                    Button(
                        onClick = { folderPickerLauncher.launch(null) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Folder, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text(if (viewModel.outputDirUri == null) "Select Folder" else "Change Folder")
                    }
                }
            }

            Spacer(Modifier.height(16.dp))


            if (games.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.Folder,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp),
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                        )
                        Spacer(Modifier.height(16.dp))
                        Text(
                            text = if (viewModel.outputDirUri == null)
                                "Select an output folder first"
                            else
                                "No downloads in progress",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(games, key = { it.titleId }) { game ->
                        val ui = viewModel.downloadStates[game.titleId] ?: DownloadUiState()
                        val isActive = viewModel.activeDownloads[game.titleId] ?: false

                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surface
                            )
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Text(
                                            text = game.name,
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                        Spacer(Modifier.height(4.dp))
                                        Text(
                                            text = "${game.region} • ${game.titleId}",
                                            style = MaterialTheme.typography.bodySmall
                                        )
                                    }

                                    if (isActive) {
                                        IconButton(
                                            onClick = {
                                                cancelDownload(game.titleId)
                                                onCancelDownload(game)
                                            }
                                        ) {
                                            Icon(
                                                Icons.Default.Close,
                                                contentDescription = "Cancel download"
                                            )
                                        }
                                    } else if (ui.isComplete) {
                                        IconButton(
                                            onClick = {
                                                // Remove the completed item from the Downloads list
                                                onCancelDownload(game)
                                                viewModel.downloadStates.remove(game.titleId)
                                                viewModel.activeDownloads.remove(game.titleId)
                                            }
                                        ) {
                                            Icon(
                                                Icons.Default.Close,
                                                contentDescription = "Remove completed"
                                            )
                                        }
                                    } else {
                                        Button(
                                            onClick = { startDownload(game) },
                                            enabled = viewModel.outputDirUri != null
                                        ) {
                                            Text("Download")
                                        }
                                    }
                                }

                                // Progress indicator with phase (only show while running)
                                if (ui.isRunning) {
                                    Spacer(Modifier.height(12.dp))

                                    // Calculate overall progress
                                    val overallProgress = when {
                                        ui.isDecrypting -> ui.decryptionProgress
                                        ui.isExtracting -> ui.extractionProgress
                                        else -> ui.progress
                                    }

                                    // Show current phase
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text(
                                            text = "${getPhaseIcon(ui.phase)} ${ui.phase.name.replace('_', ' ')}",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = getStatusColor(ui.phase),
                                            fontWeight = FontWeight.Medium
                                        )

                                        // Show progress percentage
                                        Text(
                                            text = "${(overallProgress * 100).toInt()}%",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }

                                    Spacer(Modifier.height(8.dp))

                                    // Main progress bar
                                    LinearProgressIndicator(
                                        progress = { overallProgress },
                                        modifier = Modifier.fillMaxWidth(),
                                        color = getStatusColor(ui.phase)
                                    )

                                    Spacer(Modifier.height(8.dp))

                                    // Status line
                                    Text(
                                        text = ui.status,
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 2,
                                        modifier = Modifier.fillMaxWidth()
                                    )

                                    // Download details (files and MB)
                                    if (ui.totalFiles > 0) {
                                        Spacer(Modifier.height(4.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text(
                                                text = "File ${ui.currentFile.coerceAtLeast(0)} of ${ui.totalFiles}",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                                            )
                                            if (ui.totalMB > 0) {
                                                Text(
                                                    text = "${ui.downloadedMB.toInt()} / ${ui.totalMB.toInt()} MB",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                                                )
                                            }
                                        }
                                    }

                                    // Decryption progress (if active)
                                    if (ui.isDecrypting) {
                                        Spacer(Modifier.height(8.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = "Decryption:",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.secondary,
                                                modifier = Modifier.weight(1f)
                                            )
                                            Text(
                                                text = "${(ui.decryptionProgress * 100).toInt()}%",
                                                style = MaterialTheme.typography.labelSmall,
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.secondary
                                            )
                                        }
                                        LinearProgressIndicator(
                                            progress = { ui.decryptionProgress },
                                            modifier = Modifier.fillMaxWidth(),
                                            color = MaterialTheme.colorScheme.secondary,
                                            trackColor = MaterialTheme.colorScheme.secondaryContainer
                                        )
                                    }

                                    // Extraction progress (if active)
                                    if (ui.isExtracting) {
                                        Spacer(Modifier.height(8.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = "Extraction:",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.tertiary,
                                                modifier = Modifier.weight(1f)
                                            )
                                            Text(
                                                text = "${(ui.extractionProgress * 100).toInt()}%",
                                                style = MaterialTheme.typography.labelSmall,
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.tertiary
                                            )
                                        }
                                        LinearProgressIndicator(
                                            progress = { ui.extractionProgress },
                                            modifier = Modifier.fillMaxWidth(),
                                            color = MaterialTheme.colorScheme.tertiary,
                                            trackColor = MaterialTheme.colorScheme.tertiaryContainer
                                        )
                                    }
                                }

                                if (ui.error != null) {
                                    Spacer(Modifier.height(8.dp))
                                    Text(
                                        text = ui.error,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.error
                                    )
                                }

                                if (ui.isComplete) {
                                    Spacer(Modifier.height(8.dp))
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(
                                            Icons.Default.Folder,
                                            contentDescription = null,
                                            modifier = Modifier.size(16.dp),
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                        Spacer(Modifier.width(4.dp))
                                        Text(
                                            text = "✓ Download Complete",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                    if (ui.outputPath != null) {
                                        Spacer(Modifier.height(4.dp))
                                        Text(
                                            text = ui.outputPath,
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                                            maxLines = 1,
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                    }

                                    // Show summary
                                    if (ui.totalFiles > 0) {
                                        Spacer(Modifier.height(4.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Text(
                                                text = "${ui.totalFiles} files",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                                            )
                                            if (ui.totalMB > 0) {
                                                Text(
                                                    text = "${ui.totalMB.toInt()} MB total",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// You'll also need to update your DownloadService to send these extra details:
// 1. MB downloaded/total
// 2. Current phase (INITIALIZING, DOWNLOADING_CONTENT, DECRYPTING, etc.)
// 3. Decryption/extraction progress percentages
// 4. Whether it's decrypting/extracting

/**
 * Example of how to update the sendProgress function in DownloadService:
 *
 * private fun sendProgress(
 *     titleId: String,
 *     running: Boolean,
 *     status: String,
 *     msg: String?,
 *     cur: Int,
 *     total: Int,
 *     result: String?,
 *     downloadedMB: Float = 0f,
 *     totalMB: Float = 0f,
 *     phase: DownloadPhase = DownloadPhase.IDLE,
 *     decryptionProgress: Float = 0f,
 *     extractionProgress: Float = 0f,
 *     isDecrypting: Boolean = false,
 *     isExtracting: Boolean = false
 * ) {
 *     val i = Intent(DownloadServiceConstants.ACTION_PROGRESS).apply {
 *         putExtra(DownloadServiceConstants.EXTRA_TITLE, titleId)
 *         putExtra(DownloadServiceConstants.EXTRA_RUNNING, running)
 *         putExtra(DownloadServiceConstants.EXTRA_STATUS, status)
 *         putExtra(DownloadServiceConstants.EXTRA_MSG, msg)
 *         putExtra(DownloadServiceConstants.EXTRA_CUR, cur)
 *         putExtra(DownloadServiceConstants.EXTRA_TOTAL, total)
 *         putExtra(DownloadServiceConstants.EXTRA_RESULT, result)
 *         putExtra(DownloadServiceConstants.EXTRA_DOWNLOADED_MB, downloadedMB)
 *         putExtra(DownloadServiceConstants.EXTRA_TOTAL_MB, totalMB)
 *         putExtra(DownloadServiceConstants.EXTRA_PHASE, phase.name)
 *         putExtra(DownloadServiceConstants.EXTRA_DECRYPTION_PROGRESS, decryptionProgress)
 *         putExtra(DownloadServiceConstants.EXTRA_EXTRACTION_PROGRESS, extractionProgress)
 *         putExtra(DownloadServiceConstants.EXTRA_IS_DECRYPTING, isDecrypting)
 *         putExtra(DownloadServiceConstants.EXTRA_IS_EXTRACTING, isExtracting)
 *     }
 *     sendBroadcast(i)
 * }
 */