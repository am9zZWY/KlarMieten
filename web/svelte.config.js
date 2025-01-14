import {default as bunAdapter} from "svelte-adapter-bun";
import {default as autoAdapter} from '@sveltejs/adapter-auto';
import {default as vercelAdapter} from '@sveltejs/adapter-vercel';
import {vitePreprocess} from '@sveltejs/vite-plugin-svelte';

const adapterType = process.env.ADAPTER || "auto"

const _bunAdapter = bunAdapter({
	out: "build",
	assets: true,
	development: process.env.NODE_ENV === "development",
	// precompress: true,
	precompress: {
		brotli: true,
		gzip: true,
		files: ["htm", "html"],
	},
	dynamic_origin: true,
	xff_depth: 1,
})

const _vercelAdapter = vercelAdapter({
	out: "build",
	assets: true,
	development: process.env.NODE_ENV === "development",
	// precompress: true,
	precompress: {
		brotli: true,
		gzip: true,
		files: ["htm", "html"],
	},
	dynamic_origin: true,
	xff_depth: 1,
})

const _autoAdapter = autoAdapter()

let adapter = _autoAdapter
if (adapterType === "BUN") {
	adapter = _bunAdapter
} else if (adapterType === "VERCEL") {
	adapter = _vercelAdapter
}

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
		// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
		// See https://svelte.dev/docs/kit/adapters for more information about adapters.
		adapter,
	}
};

export default config;
