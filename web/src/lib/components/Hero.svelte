<section class="hero">
    <div class="hero-content">
        <h1>Mieterrechte einfach verstehen.</h1>
        <p>KI-gestützte Analyse Ihrer Mietverträge.</p>

        {@render children?.()}
    </div>
</section>

<script>
	let {children = null} = $props();
</script>

<style>
    .hero {
        min-height: 90vh;
        display: flex;
        align-items: center;
        background: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)),
        url('$lib/images/hero.webp') no-repeat center center;
        background-size: cover;
        color: white;
        padding: 2rem;
    }

    .hero-content {
        max-width: 800px;
        margin: 0 auto;
    }

    h1 {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
</style>
