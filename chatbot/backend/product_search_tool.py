import pandas as pd
import re
from rank_bm25 import BM25Okapi
import numpy as np
import time
from nltk.stem import PorterStemmer

"""
def _lookup_product_info(
    self,
    query: Annotated[str, "The product related question or search criteria"],
    weight: Annotated[Optional[float],
        "Weight of the product in pounds"] = None,
    height: Annotated[Optional[float],
        "Height of the product in inches"] = None,
    width: Annotated[Optional[float], "Width of the product in inches"] = None,
    length: Annotated[Optional[float],
        "Length of the product in inches"] = None,
    sku: Annotated[Optional[str], "Product SKU/part number"] = None
) -> dict:
    \"""Tool for querying product information with optional dimensional specifications.\"""
    result = self.product_search_tool(
        query=query,
        weight=weight,
        height=height, # Not in the data so far so no code written for it
        width=width,
        length=length,
        sku=sku
    )
    return {"messages": [AIMessage(content=result)]}
"""
DEFAULT_MAX_RESULTS = 100
MAX_PERCENT_DIFFERENCE = 0.5
DIMENSION_SCORE_MULTIPLIER = 3.0
SKU_MATCH_SCORE = 10.0
LOW_DIMENSION_SCORE_PENALTY = 0.25
DIMENSION_SCORE_THRESHOLD_FACTOR = 0.5


def custom_tokenizer(text):
    """Custom tokenizer that preserves hyphenated words and special patterns and applies stemming"""
    text = re.sub(r'(\d+[-]\w+|\w+[-]\w+)',
                  lambda m: m.group().replace('-', '_HYPHEN_'), text)

    # Extract tokens, preserving specific patterns
    tokens = re.findall(r'\b\w+(?:_HYPHEN_\w+)*\b', text.lower())
    tokens = [token.replace('_HYPHEN_', '-') for token in tokens]

    # Stemming
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(token) for token in tokens]

    combined_tokens = list(set(stemmed_tokens + tokens))

    return combined_tokens


class ProductSearchTool:
    def __init__(self, csv_file="data.csv"):
        self.df = pd.read_csv(csv_file)
        self.df = self.df.fillna('')
        self.stemmer = PorterStemmer()
        self.prepare_search_index()

    # Define the relevant fields to keep in the response
    RELEVANT_FIELDS = [
        "ID", "SKU", "Name", "Short description", "Description", "Tax status",
        "In stock?", "Weight (lbs)", "Length (in)", "Width (in)",
        "Regular price", "Categories", "Supabase_ID", "search_text"
    ]

    def prepare_search_index(self):
        columns = [
            "ID", "Type", "SKU", "GTIN, UPC, EAN, or ISBN", "Name", "Published", "Is featured?",
            "Visibility in catalog", "Short description", "Description", "Tax status", "In stock?", "Stock",
            "Backorders allowed?", "Sold individually?", "Weight (lbs)", "Length (in)", "Width (in)",
            "Allow customer reviews?", "Regular price", "Categories", "Position", "Meta: _wp_page_template", "Supabase_ID"
        ]

        existing_columns = [col for col in columns if col in self.df.columns]

        self.df['search_text'] = self.df[existing_columns].astype(
            str).agg(' '.join, axis=1)

        self.tokenized = [custom_tokenizer(text)
                          for text in self.df['search_text']]
        self.bm25 = BM25Okapi(self.tokenized)

        for col in ["Weight (lbs)", "Length (in)", "Width (in)"]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

    def get_matched_terms(self, query):
        """get important terms from the query that are in our vocabulary"""
        query_tokens = custom_tokenizer(query)

        all_terms = set()
        for doc_tokens in self.tokenized:
            all_terms.update(doc_tokens)

        matched_terms = [term for term in query_tokens if term in all_terms]

        # adjacent terms check
        for i in range(len(query_tokens) - 1):
            bigram = f"{query_tokens[i]} {query_tokens[i+1]}"
            if any(bigram in ' '.join(doc) for doc in self.tokenized):
                matched_terms.append(bigram)

        return matched_terms

    def calculate_dimensional_score(self, row, weight=None, height=None, width=None, length=None):
        """Calculate proximity score for dimensional attributes"""
        total_score = 0
        dimensions_requested = 0
        dimensions_found = 0
        dimension_scores = {}

        if weight is not None:
            dimensions_requested += 1
        if length is not None:
            dimensions_requested += 1
        if width is not None:
            dimensions_requested += 1
        if height is not None:
            dimensions_requested += 1

        if dimensions_requested == 0:
            return 0

        def proximity_score(target, actual, dimension_type='weight'):
            # make sure we have numeric values
            if pd.isna(actual) or actual == '' or actual == 0:
                return None
            try:
                actual = float(actual)
                target = float(target)
                diff = abs(target - actual)

                # We score only up to the defined maximum percentage difference
                max_percent_diff = MAX_PERCENT_DIFFERENCE
                percent_diff = diff / max(target, actual)
                score = max(0, 1 - (percent_diff / max_percent_diff))
                return score

            except (ValueError, TypeError) as e:
                print(
                    f"Error in proximity_score: {e}, target={target}, actual={actual}")
                return None

        if weight is not None:
            i = list(self.df.columns).index("Weight (lbs)")
            actual_weight = row[i + 1]
            weight_score = proximity_score(weight, actual_weight, 'weight')
            if weight_score is not None:
                dimension_scores['weight'] = weight_score
                total_score += weight_score
                dimensions_found += 1

        if length is not None:
            i = list(self.df.columns).index("Length (in)")
            actual_length = row[i + 1]
            length_score = proximity_score(length, actual_length, 'length')
            if length_score is not None:
                dimension_scores['length'] = length_score
                total_score += length_score
                dimensions_found += 1

        if width is not None:
            i = list(self.df.columns).index("Width (in)")
            actual_width = row[i + 1]
            width_score = proximity_score(width, actual_width, 'width')
            if width_score is not None:
                dimension_scores['width'] = width_score
                total_score += width_score
                dimensions_found += 1

        if height is not None:
            i = list(self.df.columns).index("Height (in)")
            actual_height = row[i + 1]
            height_score = proximity_score(height, actual_height, 'height')
            if height_score is not None:
                dimension_scores['height'] = height_score
                total_score += height_score
                dimensions_found += 1

        if dimensions_found == 0:
            return 0

        return total_score * (dimensions_found / dimensions_requested**2)

    def search(self, query, weight=None, height=None, width=None, length=None, sku=None, max_results=DEFAULT_MAX_RESULTS):
        """Search products using BM25 ranking and dimensional parameters"""
        query_tokens = custom_tokenizer(query)
        text_scores = self.bm25.get_scores(query_tokens)

        dim_scores = np.zeros(len(self.df))
        has_dim_params = any(param is not None for param in [
                             weight, width, length, height, sku])

        # Only calculate dimensional scores if we have parameters
        if has_dim_params:
            print(
                f"Calculating dimensional scores with weight={weight}, width={width}, length={length}, height={height}")

            # Calculate dimensional scores
            for i, row in enumerate(self.df.itertuples()):

                # if SKU matches then we just give it the maximum score for both categories combined
                if sku is not None:
                    if str(getattr(row, 'SKU', '')).lower() == str(sku).lower():
                        product_dict = self.df.iloc[i].to_dict()
                        product_dict.update({
                            'score': float(SKU_MATCH_SCORE),
                            'text_score': float(SKU_MATCH_SCORE),
                            'dim_score': float(SKU_MATCH_SCORE),
                            'matched_terms': custom_tokenizer(query)
                        })

                        filtered_product = self.filter_product_fields(
                            product_dict, weight, height, width, length)

                        return [{
                            'product': filtered_product,
                            'score': SKU_MATCH_SCORE,
                            'text_score': SKU_MATCH_SCORE,
                            'dim_score': SKU_MATCH_SCORE,
                        }]

                dim_score = self.calculate_dimensional_score(
                    row, weight=weight, height=height, width=width, length=length)
                dim_scores[i] += dim_score * DIMENSION_SCORE_MULTIPLIER

        # Combine scores
        if has_dim_params:
            combined_scores = text_scores + dim_scores

            # penalty
            max_dim_score = np.max(dim_scores) if np.max(dim_scores) > 0 else 1
            dim_score_threshold = max_dim_score * DIMENSION_SCORE_THRESHOLD_FACTOR
            for i, dim_score in enumerate(dim_scores):
                if dim_score < dim_score_threshold:
                    combined_scores[i] *= LOW_DIMENSION_SCORE_PENALTY
        else:
            combined_scores = text_scores

        ranked_indices = np.argsort(combined_scores)[::-1][:max_results]

        results = []
        sorted_scores = sorted(combined_scores, reverse=True)
        score_diffs = [sorted_scores[i] - sorted_scores[i + 1]
                       for i in range(len(sorted_scores) - 1)]
        largest_drop = max(score_diffs) if score_diffs else 0
        prev_score = None

        for i in ranked_indices:
            if combined_scores[i] > 0:
                # get rid of extra results
                if prev_score and (prev_score - combined_scores[i]) == largest_drop:
                    break

                result = {
                    'product': self.df.iloc[i],
                    'score': float(combined_scores[i]),
                    'text_score': float(text_scores[i]),
                }
                prev_score = combined_scores[i]

                if has_dim_params:
                    result['dim_score'] = float(dim_scores[i])

                    if weight is not None:
                        product_weight = self.df.iloc[i]['Weight (lbs)']
                        if not pd.isna(product_weight):
                            result['weight_diff'] = abs(
                                weight - product_weight)
                        else:
                            result['weight_diff'] = 'N/A'

                    if width is not None:
                        product_width = self.df.iloc[i]['Width (in)']
                        if not pd.isna(product_width):
                            result['width_diff'] = abs(width - product_width)
                        else:
                            result['width_diff'] = 'N/A'

                    if length is not None:
                        product_length = self.df.iloc[i]['Length (in)']
                        if not pd.isna(product_length):
                            result['length_diff'] = abs(
                                length - product_length)
                        else:
                            result['length_diff'] = 'N/A'

                    if height is not None:
                        product_height = self.df.iloc[i]['Height (in)']
                        if not pd.isna(product_height):
                            result['height_diff'] = abs(
                                height - product_height)
                        else:
                            result['height_diff'] = 'N/A'

                result['matched_terms'] = query_tokens
                results.append(result)

        return results

    def filter_product_fields(self, product_dict, weight=None, height=None, width=None, length=None):
        """Filter product dictionary to only include the relevant fields"""
        filtered_dict = {k: v for k, v in product_dict.items()
                         if k in self.RELEVANT_FIELDS}

        for score_field in ['score', 'text_score', 'dim_score', 'matched_terms']:
            if score_field in product_dict:
                filtered_dict[score_field] = product_dict[score_field]

        if 'Supabase_ID' in product_dict:
            filtered_dict['Supabase_ID'] = product_dict['Supabase_ID']
        elif 'Supabase_ID' in product_dict:
            filtered_dict['Supabase_ID'] = product_dict['Supabase_ID']

        for dim, val in {
            'weight': weight,
            'width': width,
            'length': length,
            'height': height
        }.items():
            if val is not None:
                filtered_dict[f'target_{dim}'] = val

        return filtered_dict

    def get_response(self, query, weight=None, height=None, width=None, length=None, sku=None):
        """Get complete product data for the query and dimensional parameters"""
        if sku is not None:
            # Find exact SKU match first
            sku_match = self.df[self.df['SKU'].astype(
                str).str.lower() == str(sku).lower()]
            if not sku_match.empty:
                product_dict = sku_match.iloc[0].to_dict()
                product_dict.update({
                    'score': float(SKU_MATCH_SCORE),
                    'text_score': float(SKU_MATCH_SCORE),
                    'dim_score': float(SKU_MATCH_SCORE),
                    'matched_terms': custom_tokenizer(query),
                })

                filtered_product = self.filter_product_fields(
                    product_dict, weight, height, width, length)

                return {
                    "status": "SKU match found",
                    "products": [filtered_product]
                }

        search_results = self.search(query, weight, height, width, length, sku)

        if not search_results:
            return str({"status": "No products found", "products": []})

        products = []
        for result in search_results:
            product_dict = result['product'].to_dict()
            product_dict.update({
                'score': float(result['score']),
                'text_score': float(result['text_score']),
                'dim_score': float(result.get('dim_score', np.nan)),
                'matched_terms': result['matched_terms']
            })

            filtered_product = self.filter_product_fields(
                product_dict, weight, height, width, length)
            products.append(filtered_product)

        return str({
            "status": f"{len(products)} products found",
            "products": products
        })


if __name__ == "__main__":
    search_service = ProductSearchTool()
    test_queries = [
        "4-conductor",  # should match "Shielded Motor Drop (200010)"
        # should match "Cable in Conduit (240078)"
        {"query": "cable", "weight": 608},
        {"query": "cable", "weight": 600, "width": 1.5, "length": 12000.0},
        {"query": "cable", "sku": "170110"},  # UF/NMC-B (170110)
    ]
    print(search_service.get_response(
        "4-conductor", weight=608, width=1.5, length=12000.0))
    start_time = time.time()
    for query in test_queries:
        if isinstance(query, dict):
            print(
                f"\nSearch query: {query['query']} with parameters {', '.join([f'{k}: {v}' for k, v in query.items() if k != 'query'])}")
            print("-" * 50)
            results = search_service.search(**query)
        else:
            print(f"\nSearch query: {query}")
            print("-" * 50)
            results = search_service.search(query)

        # headers for dimension checks (not putting height because that's not in the data so far)
        if isinstance(query, dict) and ('weight' or 'length' or 'width') in query:
            print(
                f"{'Product':<40} {'Text Score':>8} {'Dim Score':>10} {'Weight (lbs)':>12}  {'Width (in)':>12}  {'Length (in)':>12} ")
            print("-" * 80)

        for result in results:
            product_name = result['product']['Name']
            # displaying dimension scores
            if 'dim_score' in result:
                weight = result['product']['Weight (lbs)']
                width = result['product']['Width (in)']
                length = result['product']['Length (in)']
                print(
                    f"{product_name:<40} {result['text_score']:>8.2f} {result['dim_score']:>10.2f} {weight:>12}  {width:>12} {length:>12}  ")
            else:
                # regular scores
                print(f"Product: {product_name}")
                print(f"Score: {result['score']}")
                print(f"Text Score: {result['text_score']}")
                print(f"Matched terms: {result['matched_terms']}")
                print("-" * 50)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.4f} seconds")
