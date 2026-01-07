import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import math

class MatchingEngine:
    def __init__(self, db_path='study_groups.db'):
        self.db_path = db_path

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def calculate_similarity_score(self, user_profile, group):
        """
        Calculate similarity score between user and group based on:
        - Subject match (highest weight)
        - Goal match (high weight)
        - Date/time preference (medium weight)
        - Group size preference (low weight)
        """
        score = 0.0
        
        # Subject match (weight: 40%)
        if user_profile.get('preferred_subjects'):
            if group['subject'] in user_profile['preferred_subjects']:
                score += 0.40
            elif user_profile['preferred_subjects'][0] == group['subject']:  # Primary subject
                score += 0.50  # Extra weight for primary subject
        
        # Goal match (weight: 30%)
        # Note: Our schema doesn't include a 'goal' field, so this is skipped
        
        # Date preference (weight: 20%)
        # Note: Our schema doesn't include a 'date' field, so this is skipped
        
        # Group size preference (weight: 10%)
        if user_profile.get('preferred_group_size'):
            if user_profile['preferred_group_size'] == 'small' and group['max_members'] <= 4:
                score += 0.10
            elif user_profile['preferred_group_size'] == 'large' and group['max_members'] > 4:
                score += 0.10
        
        return min(score, 1.0)  # Cap at 1.0

    def collaborative_filtering_score(self, user_id, group):
        """
        Use collaborative filtering to find groups based on similar users' preferences
        """
        conn = self.get_db_connection()
        
        # Find users with similar joining patterns
        query = '''
            SELECT DISTINCT gm2.user_id
            FROM group_members gm1
            JOIN group_members gm2 ON gm1.group_id = gm2.group_id
            WHERE gm1.user_id = ? AND gm2.user_id != ?
        '''
        
        similar_users = conn.execute(query, (user_id, user_id)).fetchall()
        
        if not similar_users:
            conn.close()
            return 0.0  # No similar users found
        
        # Find groups that similar users joined but this user hasn't
        similar_user_ids = [row['user_id'] for row in similar_users]
        placeholders = ','.join('?' * len(similar_user_ids))
        
        query = f'''
            SELECT sg.id, COUNT(*) as common_users
            FROM study_groups sg
            JOIN group_members gm ON sg.id = gm.group_id
            WHERE gm.user_id IN ({placeholders})
            AND sg.id NOT IN (
                SELECT group_id FROM group_members WHERE user_id = ?
            )
            AND sg.id = ?
            GROUP BY sg.id
        '''
        
        result = conn.execute(query, similar_user_ids + [user_id, group['id']]).fetchone()
        conn.close()
        
        if result:
            # Normalize based on total similar users
            cf_score = result['common_users'] / len(similar_users)
            return min(cf_score, 1.0)
        else:
            return 0.0

    def get_user_profile(self, user_id):
        """
        Get user profile based on their past behavior and preferences
        """
        conn = self.get_db_connection()
        
        # Get user's joined groups to understand preferences
        query = '''
            SELECT sg.subject, sg.name, sg.max_members
            FROM study_groups sg
            JOIN group_members gm ON sg.id = gm.group_id
            WHERE gm.user_id = ?
        '''
        
        user_groups = conn.execute(query, (user_id,)).fetchall()
        conn.close()
        
        profile = {
            'preferred_subjects': [],
            'preferred_goals': [],
            'preferred_dates': [],
            'preferred_group_size': None
        }
        
        if user_groups:
            # Analyze patterns in user's joined groups
            subjects = [g['subject'] for g in user_groups]
            # goals and dates are not available in our schema
            goals = []
            dates = []
            sizes = [g['max_members'] for g in user_groups]
            
            # Most common preferences
            profile['preferred_subjects'] = self.most_common(subjects, n=3)
            profile['preferred_goals'] = self.most_common(goals, n=3)
            profile['preferred_dates'] = self.most_common(dates, n=3)
            
            # Determine preferred group size (simple average)
            avg_size = sum(sizes) / len(sizes) if sizes else 10
            profile['preferred_group_size'] = 'small' if avg_size <= 4 else 'large'
        
        return profile

    def most_common(self, lst, n=1):
        """
        Return the n most common items in a list
        """
        count = defaultdict(int)
        for item in lst:
            count[item] += 1
        
        # Sort by count (descending) and return top n
        sorted_items = sorted(count.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:n]]

    def get_recommendations(self, user_id, limit=10):
        """
        Get group recommendations for a user using hybrid approach
        (rules + collaborative filtering)
        """
        conn = self.get_db_connection()
        
        # Get all available groups (not full and not joined by user)
        query = '''
            SELECT sg.*
            FROM study_groups sg
            WHERE sg.current_members < sg.max_members
            AND sg.id NOT IN (
                SELECT group_id FROM group_members WHERE user_id = ?
            )
        '''
        
        available_groups = conn.execute(query, (user_id,)).fetchall()
        conn.close()
        
        if not available_groups:
            return []
        
        # Get user profile
        user_profile = self.get_user_profile(user_id)
        
        # Calculate scores for each group
        scored_groups = []
        for group in available_groups:
            group_dict = dict(group)
            
            # Calculate rules-based score
            rules_score = self.calculate_similarity_score(user_profile, group_dict)
            
            # Calculate collaborative filtering score
            cf_score = self.collaborative_filtering_score(user_id, group_dict)
            
            # Hybrid score (50% rules, 50% collaborative filtering)
            final_score = 0.5 * rules_score + 0.5 * cf_score
            
            scored_groups.append({
                'group': group_dict,
                'rules_score': rules_score,
                'cf_score': cf_score,
                'final_score': final_score
            })
        
        # Sort by final score (descending) and return top recommendations
        scored_groups.sort(key=lambda x: x['final_score'], reverse=True)
        
        return scored_groups[:limit]

    def get_group_compatibility(self, user_id, group_id):
        """
        Calculate compatibility between a user and a specific group
        """
        conn = self.get_db_connection()
        
        # Get the specific group
        group = conn.execute(
            'SELECT * FROM study_groups WHERE id = ?', (group_id,)
        ).fetchone()
        
        if not group:
            conn.close()
            return None
        
        group_dict = dict(group)
        conn.close()
        
        # Get user profile
        user_profile = self.get_user_profile(user_id)
        
        # Calculate scores
        rules_score = self.calculate_similarity_score(user_profile, group_dict)
        cf_score = self.collaborative_filtering_score(user_id, group_dict)
        final_score = 0.5 * rules_score + 0.5 * cf_score
        
        return {
            'group': group_dict,
            'rules_score': rules_score,
            'cf_score': cf_score,
            'final_score': final_score
        }

# Example usage
if __name__ == "__main__":
    engine = MatchingEngine()
    
    # Example: Get recommendations for user with ID 1
    # recommendations = engine.get_recommendations(user_id=1, limit=5)
    # for rec in recommendations:
    #     print(f"Group: {rec['group']['subject']} - Score: {rec['final_score']:.2f}")