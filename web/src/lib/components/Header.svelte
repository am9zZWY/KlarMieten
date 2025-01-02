<nav>
    <ul class="nav-container">
        <li>
            <ul class="left-nav">
                <li><a class:active={pathname === '/'} href="/">Startseite</a></li>
                <li><a class:active={pathname === '/about'} href="/about">Über</a></li>
                <li><a class:active={pathname === '/price'} href="/price">Preise</a></li>
            </ul>
        </li>

        <li>
            <ul class="right-nav">
                <li><a class:active={pathname === '/analysis'} class="highlight" href="/analysis">Anmelden</a></li>
            </ul>
        </li>
    </ul>
</nav>

<script lang="ts">
    import { page } from "$app/state";
    let { pathname } = page.url;
</script>

<style>
    nav {
        color: black;
        padding: 1rem;
    }

    .nav-container {
        display: flex;
        justify-content: space-between;
        list-style: none;
        width: 100%;
        padding: 0;
    }

    .left-nav, .right-nav {
        display: flex;
        list-style: none;
        gap: 2rem;
        padding: 0;
    }

    /* Remove any potential margin/padding from wrapper li */
    .nav-container > li {
        padding: 0;
        margin: 0;
    }

    li {
        font-size: 1.2rem;
    }

    .highlight {
        background: black;
        color: var(--primary);
        padding: 0.5rem 1rem;
    }

    a {
        color: black;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    .active {
        background: var(--primary);
        color: black;
        padding: 0.5rem 1rem;
    }

    .active:hover {
        background: var(--primary-light);
    }
</style>
