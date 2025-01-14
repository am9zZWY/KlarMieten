<script>
	import Hero from '../lib/components/Hero.svelte';
	import Uploader from "$lib/components/Uploader.svelte";
</script>

<svelte:head>
    <title>Darf Vermieter das? | KI-gestützte Mietrechtsanalyse</title>
    <meta name="description" content="Darf Vermieter das? bietet eine KI-gestützte Analyse Ihrer Mietverträge an. So können Sie schnell und einfach überprüfen, ob Ihr Vermieter sich an die gesetzlichen Vorgaben hält.">
    <meta name="keywords" content="Mietrecht, Analyse, KI, Mietvertrag, Klausel, Mieterrechte">
    <meta name="author" content="Josef Müller">
    <meta name="robots" content="index, follow">
</svelte:head>

<Hero>
    <Uploader/>
</Hero>
