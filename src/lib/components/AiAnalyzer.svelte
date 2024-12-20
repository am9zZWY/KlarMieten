<script lang="ts">
    import { enhance } from '$app/forms';
    import type { SubmitFunction } from '@sveltejs/kit';

    let files: FileList;
    let query = '';
    let analyzing = false;
    let result: any = null;

    const handleSubmit: SubmitFunction = async ({ formData }) => {
        analyzing = true;

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });
            result = await response.json();
        } catch (error) {
            console.error('Analysis failed:', error);
        } finally {
            analyzing = false;
        }
    };
</script>

<section class="analyzer">
    <form use:enhance={handleSubmit} method="POST" enctype="multipart/form-data">
        <div class="input-group">
            <input
                    type="text"
                    bind:value={query}
                    placeholder="Beschreiben Sie Ihr Anliegen..."
                    required
            />

            <div class="file-upload">
                <label for="documents">
                    Dokumente hochladen (Verträge, Fotos, Chat-Verläufe)
                </label>
                <input
                        id="documents"
                        type="file"
                        bind:files
                        multiple
                        accept=".pdf,.jpg,.png,.txt"
                />
            </div>

            <button type="submit" disabled={analyzing}>
                {analyzing ? 'Analysiere...' : 'Jetzt prüfen'}
            </button>
        </div>
    </form>

    {#if result}
        <div class="result">
            <!-- Display analysis results -->
        </div>
    {/if}
</section>

<style>
    .analyzer {
        padding: 2rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .input-group {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    button {
        background: #000;
        color: white;
        padding: 1rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }

    button:disabled {
        background: #666;
    }
</style>
