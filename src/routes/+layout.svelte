<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { base } from '$app/paths';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div>
	<div
		class="px-4 pt-4 sticky top-0 z-50 bg-white text-sm underline text-gray-500 flex flex-row gap-2"
	>
		<a href="{base}/">mnac</a>
		<a href="{base}/about">about</a>
	</div>
	{@render children()}
</div>
