<nav>
    <ul class="nav-container">
        <li>
            <ul class="left-nav">
                {#each navItems as {path, label}}
                    <li>
                        <a class:active={page.url.pathname === path} href={path}>
                            {label}
                        </a>
                    </li>
                {/each}
            </ul>
        </li>

        <li>
            <ul class="right-nav">
                <li>
                    <a
                            class:active={page.url.pathname === '/login'}
                            class="highlight"
                            href="/login"
                    >
                        Anmelden
                    </a>
                </li>
            </ul>
        </li>
    </ul>
</nav>

<script lang="ts">
    import { page } from '$app/state';

    const navItems = [
        { path: '/', label: 'Startseite' },
        { path: '/about', label: 'Über' },
        { path: '/price', label: 'Preise' },
    ];
</script>

<style>
    nav {
        color: black;
        padding-bottom: 1rem;
        padding-top: 1rem;
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

    .highlight {
        background: black;
        color: var(--primary);
        padding: 0.5rem 1rem;
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
