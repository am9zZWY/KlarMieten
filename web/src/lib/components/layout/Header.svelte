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
    import './nav.css';
    import { page } from '$app/state';

    const navItems = [
        { path: '/', label: 'Startseite' },
        { path: '/about', label: 'Über' },
        { path: '/price', label: 'Preise' },
    ];
</script>
