package com.loyahdev.wiiudownloader

import android.content.Context
import android.database.Cursor
import android.database.MatrixCursor
import android.os.Environment
import android.os.ParcelFileDescriptor
import android.provider.DocumentsContract.Document
import android.provider.DocumentsContract.Root
import android.provider.DocumentsProvider
import android.webkit.MimeTypeMap
import java.io.File
import java.io.FileNotFoundException

class WorkDocumentsProvider : DocumentsProvider() {

    companion object {
        private const val ROOT_ID = "work_root"
        private const val DOC_ID_ROOT = "work_root:"
        private fun buildDocId(relPath: String) = "$ROOT_ID:$relPath"
        private fun relPathFromDocId(docId: String) = docId.substringAfter("$ROOT_ID:", "")
    }

    private fun getWorkDir(context: Context): File {
        val base = context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS) ?: context.cacheDir
        return File(base, "work").apply { mkdirs() }
    }

    private fun fileForDocId(context: Context, docId: String): File {
        val workDir = getWorkDir(context)
        val rel = relPathFromDocId(docId)
        return if (rel.isEmpty()) workDir else File(workDir, rel)
    }

    private fun docIdForFile(context: Context, file: File): String {
        val workDir = getWorkDir(context)
        val rel = file.toRelativeString(workDir).replace('\\', '/')
        return if (rel == ".") DOC_ID_ROOT else buildDocId(rel)
    }

    private fun mimeForFile(file: File): String {
        if (file.isDirectory) return Document.MIME_TYPE_DIR
        val ext = file.extension.lowercase()
        if (ext.isEmpty()) return "application/octet-stream"
        return MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) ?: "application/octet-stream"
    }

    private fun addRow(cursor: MatrixCursor, docId: String, file: File) {
        val flags = Document.FLAG_SUPPORTS_DELETE or
                Document.FLAG_SUPPORTS_RENAME or
                Document.FLAG_SUPPORTS_WRITE

        cursor.newRow()
            .add(Document.COLUMN_DOCUMENT_ID, docId)
            .add(Document.COLUMN_DISPLAY_NAME, if (file.name.isNotEmpty()) file.name else "work")
            .add(Document.COLUMN_SIZE, if (file.isFile) file.length() else null)
            .add(Document.COLUMN_MIME_TYPE, mimeForFile(file))
            .add(Document.COLUMN_LAST_MODIFIED, file.lastModified())
            .add(Document.COLUMN_FLAGS, flags)
    }

    override fun onCreate() = true

    override fun queryRoots(projection: Array<out String>?): Cursor {
        val result = MatrixCursor(projection ?: arrayOf(
            Root.COLUMN_ROOT_ID,
            Root.COLUMN_DOCUMENT_ID,
            Root.COLUMN_TITLE,
            Root.COLUMN_FLAGS
        ))

        result.newRow()
            .add(Root.COLUMN_ROOT_ID, ROOT_ID)
            .add(Root.COLUMN_DOCUMENT_ID, DOC_ID_ROOT)
            .add(Root.COLUMN_TITLE, "WiiUDownloader Work")
            .add(Root.COLUMN_FLAGS,
                Root.FLAG_SUPPORTS_CREATE or Root.FLAG_SUPPORTS_RECENTS or Root.FLAG_SUPPORTS_SEARCH
            )

        return result
    }

    override fun queryDocument(documentId: String, projection: Array<out String>?): Cursor {
        val result = MatrixCursor(projection ?: arrayOf(
            Document.COLUMN_DOCUMENT_ID,
            Document.COLUMN_DISPLAY_NAME,
            Document.COLUMN_SIZE,
            Document.COLUMN_MIME_TYPE,
            Document.COLUMN_LAST_MODIFIED,
            Document.COLUMN_FLAGS
        ))

        val ctx = context ?: return result
        val file = fileForDocId(ctx, documentId)
        if (file.exists()) addRow(result, documentId, file)
        return result
    }

    override fun queryChildDocuments(
        parentDocumentId: String,
        projection: Array<out String>?,
        sortOrder: String?
    ): Cursor {
        val result = MatrixCursor(projection ?: arrayOf(
            Document.COLUMN_DOCUMENT_ID,
            Document.COLUMN_DISPLAY_NAME,
            Document.COLUMN_SIZE,
            Document.COLUMN_MIME_TYPE,
            Document.COLUMN_LAST_MODIFIED,
            Document.COLUMN_FLAGS
        ))

        val ctx = context ?: return result
        val parent = fileForDocId(ctx, parentDocumentId)
        if (!parent.exists() || !parent.isDirectory) return result

        parent.listFiles()
            ?.sortedWith(compareBy({ !it.isDirectory }, { it.name.lowercase() }))
            ?.forEach { child -> addRow(result, docIdForFile(ctx, child), child) }

        return result
    }

    override fun openDocument(
        documentId: String,
        mode: String,
        signal: android.os.CancellationSignal?
    ): ParcelFileDescriptor {
        val ctx = context ?: throw FileNotFoundException("No context")
        val file = fileForDocId(ctx, documentId)
        if (!file.exists()) throw FileNotFoundException(file.absolutePath)
        return ParcelFileDescriptor.open(file, ParcelFileDescriptor.parseMode(mode))
    }

    override fun createDocument(parentDocumentId: String, mimeType: String, displayName: String): String {
        val ctx = context ?: throw FileNotFoundException("No context")
        val parent = fileForDocId(ctx, parentDocumentId)
        if (!parent.exists() || !parent.isDirectory) throw FileNotFoundException("Parent not found")

        val newFile = if (mimeType == Document.MIME_TYPE_DIR) {
            File(parent, displayName).apply { mkdirs() }
        } else {
            File(parent, displayName).apply { createNewFile() }
        }
        return docIdForFile(ctx, newFile)
    }

    override fun deleteDocument(documentId: String) {
        val ctx = context ?: return
        val file = fileForDocId(ctx, documentId)
        if (file.isDirectory) file.deleteRecursively() else file.delete()
    }

    override fun renameDocument(documentId: String, displayName: String): String {
        val ctx = context ?: throw FileNotFoundException("No context")
        val file = fileForDocId(ctx, documentId)
        val parent = file.parentFile ?: throw FileNotFoundException("No parent")
        val newFile = File(parent, displayName)
        if (!file.renameTo(newFile)) throw FileNotFoundException("Rename failed")
        return docIdForFile(ctx, newFile)
    }
}