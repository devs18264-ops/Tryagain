import discord
import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime, timedelta
from discord.ext import tasks
import os
import sys
from colorama import init, Fore, Style
import threading
from typing import Dict, List, Optional

init(autoreset=True)

class DiscordAccountManager:
    def __init__(self):
        self.accounts = {}  # token: client
        self.account_info = {}  # token: {client, voice_channel, guild_id, last_update}
        self.settings = {
            'auto_rotate': True,
            'rotate_interval': 360,  # 6 hours in minutes
            'check_interval': 60,  # 1 hour in minutes
            'profiles': []
        }
        self.profiles_list = []
        self.load_profiles()
        
    def load_tokens(self, filename='tokens.txt'):
        """Load tokens from text file"""
        try:
            with open(filename, 'r') as f:
                tokens = [line.strip() for line in f if line.strip()]
            print(Fore.GREEN + f"[✓] Loaded {len(tokens)} tokens from {filename}")
            return tokens
        except FileNotFoundError:
            print(Fore.RED + f"[✗] {filename} not found!")
            return []
    
    def load_profiles(self, filename='profiles.json'):
        """Load name/bio/dp profiles"""
        try:
            with open(filename, 'r') as f:
                self.profiles_list = json.load(f)
                print(Fore.GREEN + f"[✓] Loaded {len(self.profiles_list)} profiles")
        except FileNotFoundError:
            # Create default profiles
            self.profiles_list = [
                {"name": "Alpha User", "bio": "Living in VC 24/7", "avatar": None},
                {"name": "Beta Tester", "bio": "Never leaving this VC", "avatar": None},
                {"name": "Gamma Ray", "bio": "Always here 👀", "avatar": None},
                {"name": "Delta Force", "bio": "Permanent resident", "avatar": None},
            ]
            self.save_profiles()
            
    def save_profiles(self):
        with open('profiles.json', 'w') as f:
            json.dump(self.profiles_list, f, indent=4)
    
    async def change_account_profile(self, token: str, name: str = None, bio: str = None, avatar_path: str = None):
        """Change account's username, bio, and avatar"""
        client = self.accounts.get(token)
        if not client:
            return False
        
        headers = {'Authorization': token}
        
        # Change username
        if name:
            async with aiohttp.ClientSession() as session:
                async with session.patch('https://discord.com/api/v9/users/@me', 
                                        json={'username': name}, 
                                        headers=headers) as resp:
                    if resp.status == 200:
                        print(Fore.GREEN + f"[✓] Changed name to {name} for {token[:20]}...")
                    else:
                        print(Fore.RED + f"[✗] Failed to change name: {await resp.text()}")
        
        # Change bio
        if bio:
            async with aiohttp.ClientSession() as session:
                async with session.patch('https://discord.com/api/v9/users/@me/profile',
                                        json={'bio': bio},
                                        headers=headers) as resp:
                    if resp.status == 200:
                        print(Fore.GREEN + f"[✓] Changed bio for {token[:20]}...")
                    else:
                        print(Fore.RED + f"[✗] Failed to change bio")
        
        # Change avatar
        if avatar_path and os.path.exists(avatar_path):
            import base64
            with open(avatar_path, 'rb') as f:
                avatar_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            async with aiohttp.ClientSession() as session:
                async with session.patch('https://discord.com/api/v9/users/@me',
                                        json={'avatar': f'data:image/jpeg;base64,{avatar_base64}'},
                                        headers=headers) as resp:
                    if resp.status == 200:
                        print(Fore.GREEN + f"[✓] Changed avatar for {token[:20]}...")
                    else:
                        print(Fore.RED + f"[✗] Failed to change avatar")
        
        return True
    
    async def join_voice_channel(self, token: str, guild_id: int, channel_id: int):
        """Join a specific voice channel"""
        client = self.accounts.get(token)
        if not client:
            return False
        
        try:
            guild = client.get_guild(guild_id)
            if not guild:
                guild = await client.fetch_guild(guild_id)
            
            channel = guild.get_channel(channel_id)
            if not channel:
                channel = await client.fetch_channel(channel_id)
            
            if channel.type == discord.ChannelType.voice:
                await channel.connect()
                print(Fore.GREEN + f"[✓] {client.user.name} joined VC: {channel.name}")
                return True
            else:
                print(Fore.RED + f"[✗] {channel_id} is not a voice channel!")
                return False
        except Exception as e:
            print(Fore.RED + f"[✗] Failed to join VC: {e}")
            return False
    
    async def check_voice_status(self):
        """Check if accounts are still in VC every hour"""
        while True:
            await asyncio.sleep(self.settings['check_interval'] * 60)
            print(Fore.CYAN + "\n[🔍] Running voice channel check...")
            
            for token, info in self.account_info.items():
                client = info['client']
                voice_state = client.user.voice
                
                if not voice_state or not voice_state.channel:
                    print(Fore.YELLOW + f"[!] {client.user.name} left VC, rejoining...")
                    await self.join_voice_channel(token, info['guild_id'], info['voice_channel'])
                else:
                    print(Fore.GREEN + f"[✓] {client.user.name} is still in VC")
    
    async def auto_rotate_profiles(self):
        """Auto rotate all accounts' profiles every 6 hours"""
        while True:
            if not self.settings['auto_rotate']:
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(self.settings['rotate_interval'] * 60)
            print(Fore.MAGENTA + "\n[🔄] Running profile rotation...")
            
            for token in self.accounts.keys():
                profile = random.choice(self.profiles_list)
                await self.change_account_profile(
                    token, 
                    name=profile.get('name'),
                    bio=profile.get('bio'),
                    avatar_path=profile.get('avatar')
                )
                await asyncio.sleep(2)  # Rate limit protection
    
    async def interactive_menu(self):
        """Interactive menu for managing accounts"""
        while True:
            print(Fore.CYAN + "\n" + "="*50)
            print(Fore.YELLOW + "🎮 DISCORD ACCOUNT MANAGER")
            print(Fore.CYAN + "="*50)
            print(Fore.WHITE + "1. 📋 Show all accounts")
            print(Fore.WHITE + "2. 🎤 Join all accounts to VC")
            print(Fore.WHITE + "3. ✏️ Change single account profile")
            print(Fore.WHITE + "4. 🔄 Change ALL accounts profile")
            print(Fore.WHITE + "5. 📝 Manage profiles")
            print(Fore.WHITE + "6. ⚙️ Settings")
            print(Fore.WHITE + "7. 🚪 Exit")
            print(Fore.CYAN + "="*50)
            
            choice = input(Fore.GREEN + "Enter choice: ")
            
            if choice == '1':
                self.show_accounts()
            elif choice == '2':
                await self.join_all_to_vc()
            elif choice == '3':
                await self.change_single_profile()
            elif choice == '4':
                await self.change_all_profiles()
            elif choice == '5':
                await self.manage_profiles()
            elif choice == '6':
                self.manage_settings()
            elif choice == '7':
                print(Fore.RED + "Shutting down...")
                await self.shutdown()
                break
    
    def show_accounts(self):
        print(Fore.CYAN + "\n📋 Connected Accounts:")
        for i, (token, client) in enumerate(self.accounts.items(), 1):
            voice_status = "🔊 In VC" if client.user.voice and client.user.voice.channel else "🔇 Not in VC"
            print(Fore.WHITE + f"{i}. {client.user.name}#{client.user.discriminator} | {voice_status}")
    
    async def join_all_to_vc(self):
        guild_id = int(input(Fore.YELLOW + "Enter Guild ID: "))
        channel_id = int(input(Fore.YELLOW + "Enter Voice Channel ID: "))
        
        for token, client in self.accounts.items():
            await self.join_voice_channel(token, guild_id, channel_id)
            # Store info for auto-reconnect
            if token not in self.account_info:
                self.account_info[token] = {}
            self.account_info[token]['guild_id'] = guild_id
            self.account_info[token]['voice_channel'] = channel_id
            self.account_info[token]['client'] = client
            await asyncio.sleep(3)  # Delay to prevent rate limits
    
    async def change_single_profile(self):
        self.show_accounts()
        acc_num = int(input(Fore.YELLOW + "Select account number: ")) - 1
        token = list(self.accounts.keys())[acc_num]
        
        print(Fore.CYAN + "Leave blank to keep current")
        name = input(Fore.YELLOW + "New name: ") or None
        bio = input(Fore.YELLOW + "New bio: ") or None
        avatar = input(Fore.YELLOW + "Avatar path (image file): ") or None
        
        await self.change_account_profile(token, name, bio, avatar)
    
    async def change_all_profiles(self):
        profile_id = int(input(Fore.YELLOW + f"Select profile (1-{len(self.profiles_list)}): ")) - 1
        profile = self.profiles_list[profile_id]
        
        for token in self.accounts.keys():
            await self.change_account_profile(token, profile.get('name'), profile.get('bio'), profile.get('avatar'))
            await asyncio.sleep(2)
    
    async def manage_profiles(self):
        while True:
            print(Fore.CYAN + "\n📝 Profile Management")
            for i, profile in enumerate(self.profiles_list, 1):
                print(Fore.WHITE + f"{i}. {profile['name']} - {profile['bio'][:30]}...")
            print(Fore.WHITE + "a. Add new profile")
            print(Fore.WHITE + "d. Delete profile")
            print(Fore.WHITE + "b. Back")
            
            choice = input(Fore.GREEN + "Choice: ")
            
            if choice == 'a':
                name = input("Profile name: ")
                bio = input("Bio: ")
                avatar = input("Avatar path (optional): ") or None
                self.profiles_list.append({"name": name, "bio": bio, "avatar": avatar})
                self.save_profiles()
                print(Fore.GREEN + "Profile added!")
            elif choice == 'd':
                idx = int(input("Profile number to delete: ")) - 1
                self.profiles_list.pop(idx)
                self.save_profiles()
            elif choice == 'b':
                break
    
    def manage_settings(self):
        print(Fore.CYAN + "\n⚙️ Settings")
        print(Fore.WHITE + f"1. Auto-rotate profiles: {self.settings['auto_rotate']}")
        print(Fore.WHITE + f"2. Rotate interval: {self.settings['rotate_interval']} minutes")
        print(Fore.WHITE + f"3. Check interval: {self.settings['check_interval']} minutes")
        
        choice = input(Fore.GREEN + "Setting to change: ")
        
        if choice == '1':
            self.settings['auto_rotate'] = not self.settings['auto_rotate']
            print(Fore.GREEN + f"Auto-rotate set to {self.settings['auto_rotate']}")
        elif choice == '2':
            self.settings['rotate_interval'] = int(input("New interval (minutes): "))
        elif choice == '3':
            self.settings['check_interval'] = int(input("New check interval (minutes): "))
    
    async def shutdown(self):
        """Disconnect all accounts"""
        for client in self.accounts.values():
            if client.user.voice and client.user.voice.channel:
                await client.user.voice.disconnect()
            await client.close()
        sys.exit(0)
    
    async def setup_accounts(self):
        """Setup all Discord clients"""
        tokens = self.load_tokens()
        
        for token in tokens:
            try:
                intents = discord.Intents.default()
                intents.voice_states = True
                client = discord.Client(intents=intents)
                
                @client.event
                async def on_ready():
                    print(Fore.GREEN + f"[✓] Logged in as {client.user.name}#{client.user.discriminator}")
                
                await client.start(token, bot=False)
                self.accounts[token] = client
                await asyncio.sleep(2)  # Prevent login rate limits
                
            except Exception as e:
                print(Fore.RED + f"[✗] Failed to login: {e}")
    
    async def run(self):
        """Main runner"""
        print(Fore.CYAN + """
╔═══════════════════════════════════════╗
║   DISCORD ACCOUNT MANAGER v2.0       ║
║   Advanced Multi-Account Controller  ║
╚═══════════════════════════════════════╝
        """)
        
        await self.setup_accounts()
        
        if not self.accounts:
            print(Fore.RED + "No accounts loaded! Exiting...")
            return
        
        # Start background tasks
        asyncio.create_task(self.check_voice_status())
        asyncio.create_task(self.auto_rotate_profiles())
        
        # Start interactive menu
        await self.interactive_menu()

if __name__ == "__main__":
    manager = DiscordAccountManager()
    asyncio.run(manager.run())