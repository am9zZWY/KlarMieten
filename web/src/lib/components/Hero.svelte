<section class="hero">
    <div class="hero-content">
        <h1>Mieterrechte einfach verstehen.</h1>
        <p>KI-gestützte Analyse Ihrer Mietverträge.</p>

        {@render children?.()}
    </div>
</section>
<p class="image-credit">
    Bild von Kaboompics.com
</p>

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

    p.image-credit {
        font-size: 0.8rem;
    }
</style>
