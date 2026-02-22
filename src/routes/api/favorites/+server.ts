import { json } from '@sveltejs/kit';
import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';
import type { RequestHandler } from './$types';

const FAVORITES_PATH = join(process.cwd(), 'src/lib/assets/favorites.json');

export const GET: RequestHandler = async () => {
    try {
        const fileContent = await readFile(FAVORITES_PATH, 'utf-8');
        const favorites = JSON.parse(fileContent);
        return json(favorites);
    } catch (error) {
        console.error('Error reading favorites:', error);
        return json({});
    }
};

export const POST: RequestHandler = async ({ request }) => {
    try {
        const { imageKey, isFavorite } = await request.json();

        // Read the current favorites
        let favorites: Record<string, boolean> = {};
        try {
            const fileContent = await readFile(FAVORITES_PATH, 'utf-8');
            favorites = JSON.parse(fileContent);
        } catch (error) {
            // File doesn't exist yet, start with empty object
            favorites = {};
        }

        // Update the favorite status
        if (isFavorite) {
            favorites[imageKey] = true;
        } else {
            delete favorites[imageKey];
        }

        // Write back to file
        await writeFile(FAVORITES_PATH, JSON.stringify(favorites, null, 2), 'utf-8');

        return json({ success: true, imageKey, isFavorite });
    } catch (error) {
        console.error('Error updating favorites:', error);
        return json({ error: 'Failed to update favorite' }, { status: 500 });
    }
};
