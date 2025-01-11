<section>
    <h1>Anmelden</h1>

    <form>
        <div class="form-group">
            <label for="email">E-Mail</label>
            <input type="email" id="email" name="email" required>
        </div>

        <div class="form-group">
            <label for="password">Passwort</label>
            <input type="password" id="password" name="password" required>
        </div>

        <div class="form-actions">
            <button type="submit">Anmelden</button>
            <a href="/register">Noch keinen Account? Hier registrieren</a>
        </div>
    </form>
</section>

<svelte:head>
    <title>Darf Vermieter das? | Analyse</title>
</svelte:head>

<style>
    h1 {
        margin-bottom: 2rem;
        text-align: center;
    }

    .form-group {
        margin-bottom: 1.5rem;
    }

    label {
        display: block;
        font-weight: 500;
        margin-bottom: 0.5rem;
        color: #333;
    }

    input {
        width: 100%;
        padding: 0.75rem;
        border: 2px solid #e1e1e1;
        font-size: 1rem;
        transition: border-color 0.3s ease;
    }

    input:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
    }

    .form-actions {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        align-items: center;
        margin-top: 2rem;
    }
</style>
