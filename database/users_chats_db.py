import motor.motor_asyncio
from sample_info import tempDict
from info import (
    DATABASE_NAME, DATABASE_URI, SECONDDB_URI,
    IMDB, IMDB_TEMPLATE, MELCOW_NEW_USERS, P_TTI_SHOW_OFF,
    SINGLE_BUTTON, SPELL_CHECK_REPLY, PROTECT_CONTENT,
    AUTO_DELETE, MAX_BTN, AUTO_FFILTER
)

class Database:
    
    def __init__(self, database_name):
        # Initialize primary database connection
        self._client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        
        # Initialize secondary database connection
        self._client2 = motor.motor_asyncio.AsyncIOMotorClient(SECONDDB_URI)
        self.db2 = self._client2[database_name]
        self.col2 = self.db2.users
        self.grp2 = self.db2.groups

    def new_user(self, id, name):
        """Create a new user document."""
        return {
            'id': id,
            'name': name,
            'ban_status': {
                'is_banned': False,
                'ban_reason': "",
            }
        }

    def new_group(self, id, title):
        """Create a new group document."""
        return {
            'id': id,
            'title': title,
            'chat_status': {
                'is_disabled': False,
                'reason': "",
            }
        }
    
    async def add_user(self, id, name):
        """Add a new user to the appropriate database."""
        user = self.new_user(id, name)
        db_to_use = self.db if tempDict['indexDB'] == DATABASE_URI else self.db2
        await db_to_use.users.insert_one(user)
    
    async def is_user_exist(self, id):
        """Check if a user exists in either database."""
        user = await self.col.find_one({'id': int(id)})
        if not user:
            user = await self.col2.find_one({'id': int(id)})
        return bool(user)
    
    async def total_users_count(self):
        """Count total users across both databases."""
        count = await self.col.count_documents({}) + await self.col2.count_documents({})
        return count
    
    async def remove_ban(self, id):
        """Remove ban status for a user."""
        ban_status = {'is_banned': False, 'ban_reason': ''}
        db_to_use = self.db if await self.col.find_one({'id': int(id)}) else self.db2
        await db_to_use.users.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        """Ban a user."""
        ban_status = {'is_banned': True, 'ban_reason': ban_reason}
        db_to_use = self.db if await self.col.find_one({'id': int(user_id)}) else self.db2
        await db_to_use.users.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        """Get ban status for a user."""
        default = {'is_banned': False, 'ban_reason': ''}
        user = await self.col.find_one({'id': int(id)}) or await self.col2.find_one({'id': int(id)})
        return user.get('ban_status', default)

    async def get_all_users(self):
        """Fetch all users from both databases."""
        async for user in self.col.find({}):
            yield user
        async for user in self.col2.find({}):
            yield user
    
    async def delete_user(self, user_id):
        """Delete a user from the appropriate database."""
        db_to_use = self.db if await self.col.find_one({'id': int(user_id)}) else self.db2
        await db_to_use.users.delete_many({'id': int(user_id)})

    async def get_banned(self):
        """Get IDs of all banned users and disabled chats."""
    
        async def fetch_banned_users(db):
            async for item in db.find({'ban_status.is_banned': True}):
                yield item['id']
     
        async def fetch_disabled_chats(db):
            async for item in db.find({'chat_status.is_disabled': True}):
                yield item['id']
    
        # Collect banned users and disabled chats using async for loops
        banned_users = []
        async for user_id in fetch_banned_users(self.col):
            banned_users.append(user_id)
        async for user_id in fetch_banned_users(self.col2):
            banned_users.append(user_id)
    
        disabled_chats = []
        async for chat_id in fetch_disabled_chats(self.grp):
            disabled_chats.append(chat_id)
        async for chat_id in fetch_disabled_chats(self.grp2):
            disabled_chats.append(chat_id)
    
        return banned_users, disabled_chats
    
    async def add_chat(self, chat, title):
        """Add a new chat to the appropriate database."""
        chat_doc = self.new_group(chat, title)
        db_to_use = self.db if tempDict['indexDB'] == DATABASE_URI else self.db2
        await db_to_use.groups.insert_one(chat_doc)
    
    async def get_chat(self, id):
        """Get chat status for a given chat ID."""
        chat = await self.grp.find_one({'id': int(id)}) or await self.grp2.find_one({'id': int(id)})
        return chat.get('chat_status') if chat else False
    
    async def re_enable_chat(self, id):
        """Re-enable a disabled chat."""
        chat_status = {'is_disabled': False, 'reason': ''}
        db_to_use = self.db if await self.grp.find_one({'id': int(id)}) else self.db2
        await db_to_use.groups.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
    
    async def update_settings(self, id, settings):
        """Update settings for a chat."""
        db_to_use = self.db if await self.grp.find_one({'id': int(id)}) else self.db2
        await db_to_use.groups.update_one({'id': int(id)}, {'$set': {'settings': settings}})
    
    async def get_settings(self, id):
        """Get settings for a chat."""
        default_settings = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'auto_delete': AUTO_DELETE,
            'auto_ffilter': AUTO_FFILTER,
            'max_btn': MAX_BTN,
            'template': IMDB_TEMPLATE
        }
        chat = await self.grp.find_one({'id': int(id)}) or await self.grp2.find_one({'id': int(id)})
        return chat.get('settings', default_settings) if chat else default_settings
    
    async def disable_chat(self, chat, reason="No Reason"):
        """Disable a chat."""
        chat_status = {'is_disabled': True, 'reason': reason}
        db_to_use = self.db if await self.grp.find_one({'id': int(chat)}) else self.db2
        await db_to_use.groups.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})
    
    async def total_chat_count(self):
        """Count total chats across both databases."""
        count = await self.grp.count_documents({}) + await self.grp2.count_documents({})
        return count
    
    async def get_all_chats(self):
        """Fetch all chats from both databases."""
        all_chats = await self.grp.find({}).to_list(None) + await self.grp2.find({}).to_list(None)
        return all_chats

# Example usage:
db = Database(DATABASE_NAME)
