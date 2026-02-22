<script>
	import { onMount } from 'svelte';
	import data from '$lib/assets/all_metadata.json';

	const imageModules = import.meta.glob(
		'$lib/assets/images/*.{avif,gif,heif,jpeg,jpg,png,tiff,webp}',
		{ query: '?url', import: 'default' }
	);

	const imagePaths = Object.keys(imageModules);

	let resolvedUrls = new Map();
	let favorites = new Set();
	let showOnlyFavorites = false;
	let grayscale = false;
	let contrast = 100;

	function resetFilters() {
		grayscale = false;
		contrast = 100;
	}

	$: filteredPaths = showOnlyFavorites
		? imagePaths.filter((path) => favorites.has(path))
		: imagePaths;

	$: imageFilter = `grayscale(${grayscale ? 1 : 0}) contrast(${contrast}%)`;

	// Load favorites from localStorage
	function loadFavorites() {
		try {
			const stored = localStorage.getItem('favorites');
			if (stored) {
				const favoritesData = JSON.parse(stored);
				favorites = new Set(
					Object.keys(favoritesData)
						.map((key) => imagePaths.find((path) => getImageKey(path) === key))
						.filter(Boolean)
				);
			}
		} catch (error) {
			console.error('Error loading favorites:', error);
		}
	}

	// Load favorites on mount (browser only)
	onMount(() => {
		loadFavorites();
	});

	function toggleFavorite(path, event) {
		event?.preventDefault();
		event?.stopPropagation();

		const imageKey = getImageKey(path);
		const isFavorite = !favorites.has(path);

		if (isFavorite) {
			favorites.add(path);
		} else {
			favorites.delete(path);
		}
		favorites = favorites;

		// Save to localStorage
		try {
			const stored = localStorage.getItem('favorites');
			const favoritesData = stored ? JSON.parse(stored) : {};
			if (isFavorite) {
				favoritesData[imageKey] = true;
			} else {
				delete favoritesData[imageKey];
			}
			localStorage.setItem('favorites', JSON.stringify(favoritesData));
		} catch (error) {
			console.error('Error saving favorite:', error);
			// Revert on error
			if (isFavorite) {
				favorites.delete(path);
			} else {
				favorites.add(path);
			}
			favorites = favorites;
		}
	}

	function getImageKey(path) {
		return path
			.split('/')
			.pop()
			.replace(/\.(jpg|jpeg|png|gif|webp|avif|tiff|heif)$/i, '');
	}

	function getImageData(path) {
		const key = getImageKey(path);
		return data[key];
	}

	function inView(node) {
		const observer = new IntersectionObserver(
			([entry]) => {
				if (entry.isIntersecting) {
					node.dispatchEvent(new CustomEvent('visible'));
					observer.disconnect();
				}
			},
			{ rootMargin: '200px', threshold: 0.01 }
		);

		observer.observe(node);

		return {
			destroy() {
				observer.disconnect();
			}
		};
	}

	async function resolveUrl(path) {
		if (resolvedUrls.has(path)) return;
		const url = await imageModules[path]();
		resolvedUrls.set(path, url);
		resolvedUrls = resolvedUrls;
	}

	function magnify(node) {
		let magnifier;
		const zoomLevel = 5;
		const magnifierSize = 500;

		function handleMouseMove(e) {
			if (!magnifier) {
				magnifier = document.createElement('div');
				magnifier.className = 'magnifier';
				document.body.appendChild(magnifier);
			}

			const rect = node.getBoundingClientRect();
			const x = e.clientX - rect.left;
			const y = e.clientY - rect.top;

			if (x >= 0 && y >= 0 && x <= rect.width && y <= rect.height) {
				magnifier.style.display = 'block';
				magnifier.style.left = e.clientX - magnifierSize / 2 + 'px';
				magnifier.style.top = e.clientY - magnifierSize / 2 + 'px';

				const bgX = x * zoomLevel - magnifierSize / 2;
				const bgY = y * zoomLevel - magnifierSize / 2;

				magnifier.style.backgroundImage = `url(${node.src})`;
				magnifier.style.backgroundSize = `${rect.width * zoomLevel}px ${rect.height * zoomLevel}px`;
				magnifier.style.backgroundPosition = `-${bgX}px -${bgY}px`;
				magnifier.style.filter = imageFilter;
			}
		}

		function handleMouseLeave() {
			if (magnifier) {
				magnifier.style.display = 'none';
			}
		}

		node.addEventListener('mousemove', handleMouseMove);
		node.addEventListener('mouseleave', handleMouseLeave);

		return {
			destroy() {
				node.removeEventListener('mousemove', handleMouseMove);
				node.removeEventListener('mouseleave', handleMouseLeave);
				if (magnifier && magnifier.parentNode) {
					magnifier.parentNode.removeChild(magnifier);
				}
			}
		};
	}
</script>

<div class="border-b border-gray-200 bg-white sticky top-0 z-50 pb-4 px-4 pt-2">
	<div class="flex items-center gap-x-4 flex-wrap">
		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="checkbox"
				bind:checked={showOnlyFavorites}
				class="w-4 h-4 text-red-500 border-gray-300 rounded focus:ring-red-500"
			/>
			<span class="text-sm font-medium text-gray-700">Favorites</span>
			<span class="text-xs text-gray-500">({favorites.size})</span>
		</label>

		<div class="h-6 w-px bg-gray-300"></div>

		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="checkbox"
				bind:checked={grayscale}
				class="w-4 h-4 text-gray-600 border-gray-300 rounded focus:ring-gray-500"
			/>
			<span class="text-sm font-medium text-gray-700">Grayscale</span>
		</label>

		<label class="flex items-center gap-3">
			<span class="text-sm font-medium text-gray-700">Contrast:</span>
			<input
				type="range"
				bind:value={contrast}
				min="50"
				max="200"
				step="5"
				class="w-32 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-gray-600"
			/>
			<span class="text-xs text-gray-600 w-10">{contrast}%</span>
		</label>
		<button
			type="button"
			class="px-3 py-1 bg-gray-100 rounded hover:bg-gray-200 transition-colors duration-200"
			on:click={resetFilters}
		>
			reset
		</button>
	</div>
</div>

<div class="grid grid-flow-row-dense xl:grid-cols-4 lg:grid-cols-2 grid-cols-1 place-items-center">
	{#each filteredPaths as path (path)}
		{@const imageData = getImageData(path)}
		<div class="p-10" use:inView on:visible={() => resolveUrl(path)}>
			{#if resolvedUrls.has(path) && imageData}
				<div class="flex flex-col gap-2">
					<a
						href={resolvedUrls.get(path)}
						target="_blank"
						rel="noopener noreferrer"
						class="cursor-pointer block relative overflow-hidden"
					>
						<img
							src={resolvedUrls.get(path)}
							alt="Gallery image"
							loading="lazy"
							use:magnify
							style="filter: {imageFilter};"
						/>
					</a>
					<div class="flex flex-col gap-0.5">
						<div class="flex items-center gap-1">
							<button
								type="button"
								class="cursor-pointer flex items-center justify-center p-0 transition-transform duration-200 hover:scale-110"
								on:click={(e) => toggleFavorite(path, e)}
								aria-label="Toggle favorite"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill={favorites.has(path) ? 'currentColor' : 'none'}
									stroke="currentColor"
									stroke-width="2"
									class="w-4 h-4 text-gray-500 transition-all duration-200"
								>
									<path
										d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
									/>
								</svg>
							</button>
							<a class="hover:underline" href={imageData.url}>{imageData.title}</a>
						</div>
						<div class="text-sm text-gray-600 font-medium">{imageData.author}</div>
						<div class="text-sm text-gray-600">{imageData.info.split(';')[2]}</div>
					</div>
				</div>
			{:else}
				<div class="placeholder"></div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.placeholder {
		width: 300px;
		height: 200px;
	}

	:global(.magnifier) {
		position: fixed;
		width: 500px;
		height: 500px;
		border: 3px solid #fff;
		border-radius: 50%;
		cursor: none;
		pointer-events: none;
		display: none;
		background-repeat: no-repeat;
		box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
		z-index: 9999;
	}
</style>
