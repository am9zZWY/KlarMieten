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
    import './nav.css';
    import { page } from "$app/state";

    let { pathname } = page.url;
</script>
