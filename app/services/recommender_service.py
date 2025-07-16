import os
import pickle
from flask import current_app

# Dummy recommender implementation to avoid dependency issues
# Original imports were:
# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import pickle
# import os
# from flask import current_app

class ResearcherRecommender:
    def __init__(self, model_name='all-mpnet-base-v2'):
        """Initializes the dummy recommender service."""
        # Don't use current_app here, as it might be called outside app context
        print("Initializing dummy ResearcherRecommender (compatibility mode)")
        self.model = None
        self.dimension = 768  # Default dimension
        self.index = None
        self.index_to_user_id_map = []  # List where index matches FAISS index, value is registered_user_id
        self.user_id_to_index_map = {}  # Dict for quick lookup: {registered_user_id: faiss_index}

    def load_index(self, index_path="instance/recommender/user_index.faiss"):
        """Dummy implementation of load_index that doesn't use FAISS."""
        print("Using dummy recommender service (compatibility mode)")
        return True  # Pretend it worked

    def build_and_save_index(self, index_path="instance/recommender/user_index.faiss"):
        """
        Dummy implementation of the build_and_save_index method.
        In the original implementation, this would build a FAISS index from user data.
        """
        print("Using dummy recommender service - build_and_save_index called (compatibility mode)")
        # Make sure the directory exists
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # We'll just create an empty map file to simulate the real implementation
        map_path = index_path + ".map"
        with open(map_path, 'wb') as f:
            pickle.dump([], f)
            
        print("Dummy recommender index 'built' successfully")
        return True

    def recommend(self, registered_user_id, top_n=5):
        """
        Dummy implementation of the recommend method.
        In the original implementation, this would return similar users based on FAISS search.
        Now it just returns an empty list.
        
        :param registered_user_id: The ID of the RegisteredUser to get recommendations for.
        :param top_n: The number of recommendations to return.
        :return: An empty list (no recommendations in dummy mode).
        """
        print(f"Using dummy recommender service - recommend called for user {registered_user_id} (compatibility mode)")
        return []  # Return empty recommendations
