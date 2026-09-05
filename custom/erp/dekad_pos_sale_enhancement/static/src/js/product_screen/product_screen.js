/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { unaccent } from "@web/core/utils/strings";


function levenshtein(a, b) {
    const m = a.length;
    const n = b.length;

    if (m === 0) return n;
    if (n === 0) return m;

    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            const cost = a[i - 1] === b[j - 1] ? 0 : 1;
            dp[i][j] = Math.min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost
            );
        }
    }

    return dp[m][n];
}

function isFuzzyMatch(searchToken, targetToken) {
    if (!searchToken || !targetToken) {
        return false;
    }

    searchToken = searchToken.toLowerCase();
    targetToken = targetToken.toLowerCase();

    // Exact / prefix / substring
    if (targetToken.includes(searchToken)) {
        return true;
    }

    const window = searchToken.length;

    const threshold =
        window <= 4 ? 1 :
        window <= 7 ? 2 :
        3;

    // Compare against every substring of the target word
    for (let i = 0; i <= targetToken.length - window; i++) {
        const part = targetToken.slice(i, i + window);

        if (levenshtein(searchToken, part) <= threshold) {
            return true;
        }
    }

    // Whole-word comparison
    return (
        levenshtein(searchToken, targetToken) <=
        Math.min(3, Math.floor(searchToken.length / 3))
    );
}

patch(ProductScreen.prototype, {
    getProductsBySearchWord(searchWord) {
        const exactMatches = super.getProductsBySearchWord(searchWord);

        const cleanedSearch = unaccent(searchWord.toLowerCase(), false).trim();
        if (!cleanedSearch) {
            return exactMatches;
        }

        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;

        const searchTokens = cleanedSearch.split(/\s+/).filter(Boolean);

        const fuzzyMatches = products.filter((product) => {
            const words = unaccent(product.searchString, false)
                .toLowerCase()
                .split(/\s+/)
                .filter(Boolean);

            return searchTokens.every((searchToken) =>
                words.some((word) => isFuzzyMatch(searchToken, word))
            );
        });

        // Merge exact and fuzzy results without duplicates.
        return [...new Set([...exactMatches, ...fuzzyMatches])];
    },
});