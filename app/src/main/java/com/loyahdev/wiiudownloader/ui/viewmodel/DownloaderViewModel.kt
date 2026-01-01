package com.loyahdev.wiiudownloader

import android.app.*
import android.content.*
import android.os.*
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import kotlin.math.roundToInt
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Job
import java.io.File
import java.io.FileInputStream
import android.provider.DocumentsContract
import android.os.Handler
import android.os.Looper
import android.os.Environment
// Removed DocumentsProvider and related unused imports from MainActivity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider



class DownloadService : Service() {

    companion object {
        const val ACTION_START = "com.loyahdev.wiiudownloader.action.START"
        const val ACTION_CANCEL = "com.loyahdev.wiiudownloader.action.CANCEL"
        const val ACTION_PROGRESS = "com.loyahdev.wiiudownloader.action.PROGRESS"

        const val EXTRA_TITLE = "extra_title"
        const val EXTRA_WORK_DIR = "extra_work_dir"
        const val EXTRA_OUTPUT_TREE = "extra_output_tree"
        const val EXTRA_DELETE_AFTER_COPY = "extra_delete_after_copy"
        const val EXTRA_AUTO_DECRYPT = "extra_auto_decrypt"
        const val EXTRA_AUTO_EXTRACT = "extra_auto_extract"

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

        private const val NOTIF_CHANNEL_ID = "download_channel"
        private const val NOTIF_ID = 1001
    }

    private val cancelToken = CancelToken()
    private var job: Job? = null
    private var currentPhase = DownloadPhase.IDLE
    private var isDecrypting = false
    private var isExtracting = false
    private var decryptionProgress = 0f
    private var extractionProgress = 0f
    private var downloadedMB = 0f
    private var totalMB = 0f

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                if (job != null) return START_STICKY
                cancelToken.reset()
                resetProgress()

                val titleId = intent.getStringExtra(EXTRA_TITLE) ?: return START_NOT_STICKY
                val workDirPath = intent.getStringExtra(EXTRA_WORK_DIR) ?: return START_NOT_STICKY
                val outputTree = intent.getStringExtra(EXTRA_OUTPUT_TREE) ?: return START_NOT_STICKY
                val deleteAfterCopy = intent.getBooleanExtra(EXTRA_DELETE_AFTER_COPY, true)
                val autoDecrypt = intent.getBooleanExtra(EXTRA_AUTO_DECRYPT, true)
                val autoExtract = intent.getBooleanExtra(EXTRA_AUTO_EXTRACT, true)

                startForeground(NOTIF_ID, buildNotif("Starting…", 0, 0, DownloadPhase.INITIALIZING))
                sendProgress(
                    titleId = titleId,
                    running = true,
                    status = "Starting…",
                    msg = "Initializing download...",
                    cur = 0,
                    total = 0,
                    result = null,
                    downloadedMB = 0f,
                    totalMB = 0f,
                    phase = DownloadPhase.INITIALIZING
                )

                job = CoroutineScope(Dispatchers.IO).launch {
                    runDownload(titleId, workDirPath, outputTree, deleteAfterCopy, autoDecrypt, autoExtract)
                }
            }
            ACTION_CANCEL -> {
                cancelToken.cancel()
                job?.cancel()
            }
        }
        return START_STICKY
    }

    private fun resetProgress() {
        currentPhase = DownloadPhase.IDLE
        isDecrypting = false
        isExtracting = false
        decryptionProgress = 0f
        extractionProgress = 0f
        downloadedMB = 0f
        totalMB = 0f
    }

    private suspend fun runDownload(
        titleId: String,
        workDirPath: String,
        outputTreeUriStr: String,
        deleteAfterCopy: Boolean,
        autoDecrypt: Boolean = true,
        autoExtract: Boolean = true
    ) {
        try {
            val workDir = File(workDirPath)
            workDir.mkdirs()

            // Enhanced ProgressBridge with all callbacks
            val bridge = EnhancedProgressBridge(
                onUpdate = { percent, msg, cur, total, downloaded, totalSize ->
                    currentPhase = DownloadPhase.DOWNLOADING_CONTENT
                    downloadedMB = downloaded
                    totalMB = totalSize

                    val notificationMsg = when {
                        msg.contains("MB") -> msg
                        total > 0 -> "File $cur/$total • ${downloaded.roundToInt()}/${totalSize.roundToInt()} MB"
                        else -> msg
                    }

                    val notification = buildNotif(notificationMsg, cur, total, currentPhase)
                    val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                    nm.notify(NOTIF_ID, notification)

                    sendProgress(
                        titleId = titleId,
                        running = true,
                        status = "Downloading...",
                        msg = msg,
                        cur = cur,
                        total = total,
                        result = null,
                        downloadedMB = downloaded,
                        totalMB = totalSize,
                        phase = currentPhase,
                        decryptionProgress = decryptionProgress,
                        extractionProgress = extractionProgress,
                        isDecrypting = isDecrypting,
                        isExtracting = isExtracting
                    )
                },
                onPhaseChange = { phase ->
                    currentPhase = phase
                    val msg = when (phase) {
                        DownloadPhase.DOWNLOADING_METADATA -> "Downloading metadata..."
                        DownloadPhase.DECRYPTING -> "Decrypting files..."
                        DownloadPhase.EXTRACTING -> "Extracting files..."
                        DownloadPhase.FINALIZING -> "Finalizing..."
                        else -> "Processing..."
                    }

                    val notification = buildNotif(msg, 0, 0, phase)
                    val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                    nm.notify(NOTIF_ID, notification)

                    sendProgress(
                        titleId = titleId,
                        running = true,
                        status = phase.name.replace("_", " "),
                        msg = msg,
                        cur = 0,
                        total = 0,
                        result = null,
                        downloadedMB = downloadedMB,
                        totalMB = totalMB,
                        phase = phase,
                        decryptionProgress = decryptionProgress,
                        extractionProgress = extractionProgress,
                        isDecrypting = isDecrypting,
                        isExtracting = isExtracting
                    )
                },
                onDecryptionProgress = { percent, message ->
                    currentPhase = DownloadPhase.DECRYPTING
                    isDecrypting = true
                    decryptionProgress = percent

                    val cleanMsg = if (message.length > 40) message.substring(0, 37) + "..." else message
                    val notification = buildNotif("Decrypting: ${percent.toInt()}%", 0, 0, currentPhase)
                    val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                    nm.notify(NOTIF_ID, notification)

                    sendProgress(
                        titleId = titleId,
                        running = true,
                        status = "Decrypting...",
                        msg = cleanMsg,
                        cur = 0,
                        total = 0,
                        result = null,
                        downloadedMB = downloadedMB,
                        totalMB = totalMB,
                        phase = currentPhase,
                        decryptionProgress = percent,
                        extractionProgress = extractionProgress,
                        isDecrypting = true,
                        isExtracting = isExtracting
                    )
                },
                onExtractionProgress = { percent, message ->
                    currentPhase = DownloadPhase.EXTRACTING
                    isExtracting = true
                    extractionProgress = percent

                    val cleanMsg = if (message.length > 40) message.substring(0, 37) + "..." else message
                    val notification = buildNotif("Extracting: ${percent.toInt()}%", 0, 0, currentPhase)
                    val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                    nm.notify(NOTIF_ID, notification)

                    sendProgress(
                        titleId = titleId,
                        running = true,
                        status = "Extracting...",
                        msg = cleanMsg,
                        cur = 0,
                        total = 0,
                        result = null,
                        downloadedMB = downloadedMB,
                        totalMB = totalMB,
                        phase = currentPhase,
                        decryptionProgress = decryptionProgress,
                        extractionProgress = percent,
                        isDecrypting = false,
                        isExtracting = true
                    )
                }
            )

            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(this))
            }

            val py = Python.getInstance()
            val mod = py.getModule("runner")

            // providerRootDocUri passed for compatibility (can be ignored by Python).
            val providerAuthority = "${packageName}.workdocuments"
            val providerRootDocUri = DocumentsContract.buildDocumentUri(providerAuthority, "work_root:").toString()

            // Call Python with additional parameters for decryption/extraction
            val pythonReturn = mod.callAttr(
                "main_with_progress",
                titleId,
                workDir.absolutePath,
                providerRootDocUri,
                bridge,
                cancelToken,
                autoDecrypt,  // auto_decrypt parameter
                deleteAfterCopy,  // delete_encrypted parameter
                autoExtract  // auto_extract parameter
            ).toString()

            if (cancelToken.is_cancelled()) {
                // Cleanup partial title folder
                File(workDir, titleId).deleteRecursively()
                sendProgress(
                    titleId = titleId,
                    running = false,
                    status = "Cancelled",
                    msg = "Download cancelled by user",
                    cur = 0,
                    total = 0,
                    result = "Download cancelled",
                    downloadedMB = downloadedMB,
                    totalMB = totalMB,
                    phase = DownloadPhase.ERROR
                )
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return
            }

            currentPhase = DownloadPhase.FINALIZING
            sendProgress(
                titleId = titleId,
                running = true,
                status = "Finalizing...",
                msg = "Copying files to destination...",
                cur = 0,
                total = 0,
                result = null,
                downloadedMB = downloadedMB,
                totalMB = totalMB,
                phase = currentPhase
            )

            val preferredTitleDir = File(workDir, titleId)
            val returnedDir = File(pythonReturn).let { returned ->
                when {
                    returned.isAbsolute -> returned
                    pythonReturn.isNotBlank() -> File(workDir, pythonReturn)
                    else -> preferredTitleDir
                }
            }

            val localDir = when {
                returnedDir.exists() && returnedDir.isDirectory && returnedDir.name.equals(titleId, ignoreCase = true) -> returnedDir
                preferredTitleDir.exists() && preferredTitleDir.isDirectory -> preferredTitleDir
                else -> throw IllegalStateException("Output folder not found. Expected ${preferredTitleDir.absolutePath}. Python returned ${returnedDir.absolutePath}.")
            }

            val outputTreeUri = Uri.parse(outputTreeUriStr)

            // Copy into user-selected destination
            val destUri = copyLocalDirToSafDir(
                context = this,
                destParentTreeUri = outputTreeUri,
                sourceDir = localDir
            )

            // Optionally delete from work folder
            if (deleteAfterCopy) {
                localDir.deleteRecursively()
                if (workDir.exists() && (workDir.listFiles()?.isEmpty() == true)) {
                    workDir.delete()
                }
            }

            val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(NOTIF_ID, buildNotif("Done", 1, 1, DownloadPhase.COMPLETE))

            currentPhase = DownloadPhase.COMPLETE

            val resultMessage = "Download complete!\n" +
                    "Folder: ${localDir.name}\n" +
                    "Size: ${totalMB.roundToInt()} MB\n" +
                    "Files: ${getFileCount(localDir)}"

            sendProgress(
                titleId = titleId,
                running = false,
                status = "Done",
                msg = "Download completed successfully",
                cur = 1,
                total = 1,
                result = resultMessage,
                downloadedMB = downloadedMB,
                totalMB = totalMB,
                phase = currentPhase
            )

        } catch (t: Throwable) {
            currentPhase = DownloadPhase.ERROR
            sendProgress(
                titleId = titleId,
                running = false,
                status = "Error",
                msg = t.message ?: t.javaClass.simpleName,
                cur = 0,
                total = 0,
                result = t.message ?: t.javaClass.simpleName,
                downloadedMB = downloadedMB,
                totalMB = totalMB,
                phase = currentPhase
            )
        } finally {
            job = null
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private fun getFileCount(directory: File): Int {
        if (!directory.exists() || !directory.isDirectory) return 0
        return directory.walk()
            .filter { it.isFile }
            .count()
    }

    private fun sendProgress(
        titleId: String,
        running: Boolean,
        status: String,
        msg: String?,
        cur: Int,
        total: Int,
        result: String?,
        downloadedMB: Float = 0f,
        totalMB: Float = 0f,
        phase: DownloadPhase = DownloadPhase.IDLE,
        decryptionProgress: Float = 0f,
        extractionProgress: Float = 0f,
        isDecrypting: Boolean = false,
        isExtracting: Boolean = false
    ) {
        val i = Intent(ACTION_PROGRESS).apply {
            setPackage(packageName)
            putExtra(EXTRA_TITLE, titleId)
            putExtra(EXTRA_RUNNING, running)
            putExtra(EXTRA_STATUS, status)
            putExtra(EXTRA_MSG, msg)
            putExtra(EXTRA_CUR, cur)
            putExtra(EXTRA_TOTAL, total)
            putExtra(EXTRA_RESULT, result)
            putExtra(EXTRA_DOWNLOADED_MB, downloadedMB)
            putExtra(EXTRA_TOTAL_MB, totalMB)
            putExtra(EXTRA_PHASE, phase.name)
            putExtra(EXTRA_DECRYPTION_PROGRESS, decryptionProgress)
            putExtra(EXTRA_EXTRACTION_PROGRESS, extractionProgress)
            putExtra(EXTRA_IS_DECRYPTING, isDecrypting)
            putExtra(EXTRA_IS_EXTRACTING, isExtracting)
        }
        sendBroadcast(i)
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            val ch = NotificationChannel(
                NOTIF_CHANNEL_ID,
                "Downloads",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Download progress notifications"
                enableVibration(false)
                enableLights(false)
            }
            nm.createNotificationChannel(ch)
        }
    }

    private fun buildNotif(text: String, cur: Int, total: Int, phase: DownloadPhase = DownloadPhase.IDLE): Notification {
        val progress = if (total > 0) ((cur.toFloat() / total.toFloat()) * 100).toInt().coerceIn(0, 100) else 0

        val phaseIcon = when (phase) {
            DownloadPhase.DOWNLOADING_CONTENT -> "⬇"
            DownloadPhase.DECRYPTING -> "🔓"
            DownloadPhase.EXTRACTING -> "📦"
            DownloadPhase.COMPLETE -> "✓"
            DownloadPhase.ERROR -> "✗"
            else -> "⚙"
        }

        val title = when (phase) {
            DownloadPhase.DOWNLOADING_CONTENT -> "$phaseIcon Downloading"
            DownloadPhase.DECRYPTING -> "$phaseIcon Decrypting"
            DownloadPhase.EXTRACTING -> "$phaseIcon Extracting"
            DownloadPhase.COMPLETE -> "$phaseIcon Complete"
            DownloadPhase.ERROR -> "$phaseIcon Error"
            else -> "$phaseIcon WiiUDownloader"
        }

        val builder = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, NOTIF_CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        return builder
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .setProgress(100, progress, total == 0)
            .build()
    }
}

// Enhanced ProgressBridge to match Python bridge interface
class EnhancedProgressBridge(
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

// Helper functions for file operations
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

// Enum for download phases
enum class DownloadPhase {
    IDLE,
    INITIALIZING,
    DOWNLOADING_METADATA,
    DOWNLOADING_CONTENT,
    DECRYPTING,
    EXTRACTING,
    FINALIZING,
    COMPLETE,
    ERROR
}