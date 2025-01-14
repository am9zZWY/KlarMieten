<div
        aria-dropeffect="copy"
        aria-label="File Upload"
        class="upload-area"
        class:dragging={isDragging}
        class:has-error={errorMessage}
        ondragleave={handleDragLeave}
        ondragover={handleDragOver}
        ondrop={handleDrop}
        onkeydown={(e) => e.key === 'Enter' && document.getElementById('fileInput')?.click()}
        role="button"
        tabindex="0"
>
    <input
            accept={ACCEPTED_FILE_TYPES.join(',')}
            hidden
            id="fileInput"
            multiple
            onchange={handleFileSelect}
            type="file"
    />
    <div class="upload-content">
        {#if files.size > 0}
            <ul class="file-preview">
                {#each files as file}
                    <li class="file">
                        {#if file.preview}
                            <img src={file.preview} alt="File Preview"/>
                        {:else}
                            <span>{file.name}</span>
                        {/if}
                        <button type="button" onclick={() => removeFile(file)} class="remove">Entfernen</button>
                    </li>
                {/each}
            </ul>
        {/if}
        <span>Ziehen Sie
            {#if files.size > 0} weitere Dateien {:else}Ihren  Mietvertrag {/if} hierher oder</span>
        <label for="fileInput">Dateien auswählen</label>
    </div>
</div>

{#if errorMessage}
    <div class="error-message" role="alert">
        {errorMessage}
    </div>
{/if}

<form class="search-box" onsubmit={handleSubmit}>
    <!-- <input
            aria-label="Beschreiben Sie Ihr Anliegen"
            bind:value={searchQuery}
            placeholder="Beschreiben Sie Ihr Anliegen..."
            type="text"
    /> -->
    <button type="submit">Prüfen</button>
</form>


<script lang="ts">
    import { onDestroy } from "svelte";
    import { SvelteSet } from "svelte/reactivity";

    type FileWithPreview = File & { preview?: string };

    // Use $state for reactive variables
    let searchQuery = $state('');
    let isDragging = $state(false);
    let files = $state<SvelteSet<FileWithPreview>>(new SvelteSet<FileWithPreview>());
    let errorMessage = $state('');

    // Constants
    const ACCEPTED_FILE_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

    function validateFile(file: File): string | null {
        if (!ACCEPTED_FILE_TYPES.includes(file.type)) {
            return 'Nur PDF, JPEG und PNG Dateien sind erlaubt.';
        }
        if (file.size > MAX_FILE_SIZE) {
            return 'Die Datei darf nicht größer als 10MB sein.';
        }
        return null;
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        isDragging = true;
    }

    function handleDragLeave(event: DragEvent) {
        // Only leave the drag state if we're not dragging over a child element
        if (event.currentTarget === event.target) {
            isDragging = false;
        }
    }

    async function handleFiles(fileList: FileList | null) {
        errorMessage = '';
        if (!fileList?.length) {
            errorMessage = 'Keine Dateien ausgewählt.';
            console.error('No files selected.');
            return;
        }

        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];

            // Validate file
            const error = validateFile(file);
            if (error) {
                errorMessage = error;
                return;
            }

            try {
                // Create file preview if it's an image
                if (file.type.startsWith('image/')) {
                    const preview = URL.createObjectURL(file);
                    files.add(Object.assign(file, { preview }));
                } else {
                    files.add(file);
                }
            } catch (err) {
                errorMessage = 'Fehler beim Verarbeiten der Datei.';
                console.error('File processing error:', err);
            }
        }
    }

    function removeFile(file: File) {
        files.delete(file)
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        isDragging = false;
        if (event.dataTransfer?.files) {
            handleFiles(event.dataTransfer?.files);
        } else {
            errorMessage = 'Fehler beim Verarbeiten der Datei.';
        }
    }

    function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        handleFiles(input.files);
    }

    function handleSubmit(event: SubmitEvent) {
        event.preventDefault();
        if (!files.size) {
            errorMessage = 'Bitte wählen Sie zuerst eine Datei aus.';
            return;
        }
        if (!searchQuery.trim()) {
            errorMessage = 'Bitte beschreiben Sie Ihr Anliegen.';
            return;
        }
    }

    // Cleanup function for file previews
    onDestroy(() => {
        files.forEach(file => {
            if (file.preview) {
                URL.revokeObjectURL(file.preview);
            }
        });
    });
</script>

<style>
    .search-box {
        display: flex;
        gap: 1rem;
        margin-top: 2rem;
    }

    input {
        flex: 1;
        padding: 1rem;
        border: none;
    }

    button.remove {
        background: #ff3333;
        color: white;
    }

    .upload-area {
        background: rgba(255, 255, 255, 0.1);
        border: 2px dashed rgba(255, 255, 255, 0.3);
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        transition: all 0.3s ease;
    }

    .upload-area.dragging {
        background: rgba(255, 255, 255, 0.2);
        border-color: var(--primary);
    }

    .upload-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }

    .upload-content label {
        color: var(--primary);
        cursor: pointer;
        text-decoration: underline;
    }

    .upload-content label:hover {
        color: var(--primary-light);
    }

    .error-message {
        background: rgba(255, 0, 0, 0.1);
        color: #ff3333;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        margin-top: 1rem;
    }

    .upload-area.has-error {
        border-color: #ff3333;
    }

    .file-preview {
        display: flex;
        align-items: flex-start;
        flex-direction: column;
        gap: 1rem;
    }

    .file {
        display: flex;
        gap: 1rem;
    }

    .file-preview img {
        max-width: 100px;
        max-height: 100px;
        object-fit: contain;
    }
</style>
