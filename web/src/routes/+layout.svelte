<script>
	import './styles.css';
	import Header from "$lib/components/layout/Header.svelte";
	import Footer from "$lib/components/layout/Footer.svelte";

	let {children} = $props();
</script>

<main>
    <Header/>
    {@render children()}
    <Footer/>
</main>
