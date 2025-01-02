<Header/>
<section>
    <h1>Vertragsanalyse</h1>
</section>

<svelte:head>
    <title>Darf Vermieter das? | Analyse</title>
</svelte:head>

<script lang="ts">
    import type { SubmitFunction } from '@sveltejs/kit';
    import Header from "$lib/components/Header.svelte";

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
