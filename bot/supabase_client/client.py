import asyncio
import os
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from .models import User

class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            # Use asyncio.to_thread to run the synchronous operation in a thread
            response = await asyncio.to_thread(
                lambda: self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            )
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        try:
            existing_user = await self.get_user_by_telegram_id(user_data['telegram_id'])
            
            if existing_user:
                response = await asyncio.to_thread(
                    lambda: self.client.table('users').update(user_data).eq('telegram_id', user_data['telegram_id']).execute()
                )
            else:
                response = await asyncio.to_thread(
                    lambda: self.client.table('users').insert(user_data).execute()
                )
            
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None
    
    async def search_automations_by_similarity(self, query_embedding: List[float], limit: int = 3, threshold: float = None) -> List[Dict[str, Any]]:
        """
        Search for similar automation documents using vector similarity
        
        Args:
            query_embedding: Query vector embedding from OpenAI (3072 dimensions)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of automation documents ranked by vector similarity
        """
        # Get threshold from environment variable if not provided
        if threshold is None:
            threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
            
        try:
            print(f"🔍 Searching for similar automations with threshold={threshold}, limit={limit}")
            
            # Get all documents with embeddings from the documents table
            response = await asyncio.to_thread(
                lambda: self.client.table('documents').select('''
                    id, url, short_description, description, name,
                    embedding, category, subcategory, tags
                ''').not_.is_('embedding', 'null').execute()
            )
            
            print(f"🔍 Raw response data count: {len(response.data) if response.data else 0}")
            if response.data and len(response.data) > 0:
                first_doc = response.data[0]
                print(f"🔍 First document structure: {list(first_doc.keys())}")
                print(f"🔍 Has embedding: {first_doc.get('embedding') is not None}")
                if first_doc.get('embedding'):
                    embedding_sample = first_doc.get('embedding')
                    print(f"🔍 Embedding type: {type(embedding_sample)}, length: {len(embedding_sample) if embedding_sample else 0}")
                    print(f"🔍 Embedding preview (first 100 chars): {str(embedding_sample)[:100]}...")
            
            # Filter out documents without embeddings manually
            if response.data:
                response.data = [doc for doc in response.data if doc.get('embedding') is not None]
                print(f"🔍 Documents with embeddings after filtering: {len(response.data)}")
            
            if not response.data:
                print("🔍 No documents with embeddings found")
                return []
            
            print(f"🔍 Retrieved {len(response.data)} automation documents with embeddings")
            
            # Calculate similarities manually
            import numpy as np
            import json
            query_vector = np.array(query_embedding)
            
            doc_similarities = []
            
            for doc in response.data:
                if doc.get('embedding'):
                    try:
                        # Parse embedding from string format (stored as JSON string)
                        embedding_str = doc['embedding']
                        if isinstance(embedding_str, str):
                            # Try to parse as JSON array
                            try:
                                embedding_data = json.loads(embedding_str)
                            except json.JSONDecodeError:
                                # If not JSON, try to evaluate as Python literal
                                embedding_data = eval(embedding_str)
                        else:
                            embedding_data = embedding_str
                        
                        doc_vector = np.array(embedding_data)
                        
                        if doc_vector.shape != query_vector.shape:
                            print(f"🔍 Dimension mismatch for doc {doc.get('id')}: query={query_vector.shape}, doc={doc_vector.shape}")
                            continue
                            
                    except Exception as parse_error:
                        print(f"🔍 Failed to parse embedding for doc {doc.get('id')}: {parse_error}")
                        continue
                    
                    # Cosine similarity calculation
                    dot_product = np.dot(query_vector, doc_vector)
                    query_norm = np.linalg.norm(query_vector)
                    doc_norm = np.linalg.norm(doc_vector)
                    
                    cosine_sim = dot_product / (query_norm * doc_norm)
                    
                    if cosine_sim > threshold:
                        # Get category name from the new schema
                        category_name = doc.get('category', 'Uncategorized')

                        # Format name as title
                        title = doc.get('name', 'Unnamed')
                        if title.endswith('.json'):
                            title = title[:-5]  # Remove .json extension
                        title = title.replace('-', ' ').replace('_', ' ').title()

                        doc_similarities.append({
                            'id': doc['id'],
                            'title': title,
                            'short_description': doc.get('short_description', ''),
                            'description': doc.get('description', ''),
                            'url': doc.get('url', ''),
                            'category': category_name,
                            'subcategory': doc.get('subcategory', ''),
                            'tags': doc.get('tags', []),
                            'similarity': float(cosine_sim)
                        })
            
            # Sort by similarity (highest first) and limit
            doc_similarities.sort(key=lambda x: x['similarity'], reverse=True)
            results = doc_similarities[:limit]
            
            print(f"🔍 Found {len(results)} similar automations above threshold {threshold}")
            for i, doc in enumerate(results):
                print(f"🔍 Rank {i+1}: {doc['title']} (similarity: {doc['similarity']:.4f})")
            
            return results
            
        except Exception as e:
            print(f"Error in automation similarity search: {e}")
            return []
    
    
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[User]:
        """Create user only if doesn't exist - for handlers compatibility"""
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return existing_user  # Don't update, just return existing user

        # Only create new user if doesn't exist
        user_data = {
            'telegram_id': telegram_id,
            'username': username
        }
        # Remove None values to avoid column errors
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('users').insert(user_data).execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def update_user_payment_status(self, telegram_id: int, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            )
            
            if response.data:
                print(f"✅ Updated payment status for user {telegram_id}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user {telegram_id}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status: {e}")
            return False
    
    async def update_user_payment_status_by_email(self, email: str, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status by email (if email field exists)"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            # Note: This assumes you have an email field in users table
            # You might need to add email field to users table first
            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(update_data).eq('email', email).execute()
            )
            
            if response.data:
                print(f"✅ Updated payment status for user with email {email}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user with email {email}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status by email: {e}")
            return False

    async def update_user_subscription(self, subscription_data: Dict[str, Any]) -> bool:
        """
        Update user subscription status

        Args:
            subscription_data: Dictionary containing subscription fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            telegram_id = subscription_data.get('telegram_id')
            if not telegram_id:
                print("Error: telegram_id is required for subscription update")
                return False

            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(subscription_data).eq('telegram_id', telegram_id).execute()
            )

            if response.data:
                print(f"✅ Updated subscription for user {telegram_id}: {subscription_data.get('subscription_status', 'unknown')}")
                return True
            else:
                print(f"❌ Failed to update subscription for user {telegram_id}")
                return False

        except Exception as e:
            print(f"Error updating user subscription: {e}")
            return False