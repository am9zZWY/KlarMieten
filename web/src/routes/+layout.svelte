<script>
	import './styles.css';
	import Header from "$lib/components/Header.svelte";
	import Footer from "$lib/components/Footer.svelte";

	let {children} = $props();
</script>

<main>
    <Header/>
    {@render children()}
    <Footer/>
</main>
