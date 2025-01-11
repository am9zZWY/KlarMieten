<nav>
    <ul class="nav-container">
        <li>
            <ul class="left-nav">
                <li><a class:active={pathname === '/dsgvo'} href="/dsgvo">Datenschutzerklärung</a></li>
            </ul>
        </li>

        <li>
            <ul class="right-nav">
                <li>Mit Liebe gemacht</li>
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

    .nav-container > li {
        padding: 0;
        margin: 0;
    }

    li {
        font-size: 1.2rem;
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
