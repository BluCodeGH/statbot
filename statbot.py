import asyncio
import datetime
import json
import math
import re
from discord import Client, AuditLogAction
from dctoken import token, owner

class StatBot(Client):
  def __init__(self, *args):
    super().__init__(*args)
    self.commands = {
        "!users": self.userStats,
        "!channels": self.channelStats,
        "!times": self.timeStats,
        "!count": self.count
    }
    try:
      with open("reaction_roles.json") as f:
        self.reaction_roles = json.load(f)
    except FileNotFoundError:
      with open("reaction_roles.json", "w+") as f:
        f.write("{}")
      self.reaction_roles = {}

  async def on_ready(self):
    print("Connected as " + str(self.user))
    await self.monitor()

  async def on_message(self, m):
    if m.author == self.user:
      return
    if m.author.id == owner:
      if m.content == "!quit":
        return await self.logout()
      if m.content.startswith("!rr"):
        return await self.rr(m)
      if m.content.startswith("!exec"):
        return await self.exec(m)
    if "stats canada" in [r.name for r in m.author.roles] and m.content.startswith("!"):
      command, *args = m.content.strip().split()
      try:
        command = self.commands[command]
      except KeyError:
        await m.channel.send("Unknown command {}.".format(command))
        return
      if args:
        try:
          delta = int(args[0])
        except ValueError:
          await m.channel.send("Invalid argument. Usage: `!<command> <months ago>`, for example `!count 2`.")
          return
      else:
        delta = 0
      t = datetime.datetime.today()
      date = datetime.datetime(t.year, t.month - delta, 1)
      async with m.channel.typing():
        status = await m.channel.send("Working...")
        res = await command(m.guild, date, status)
        await status.delete()
        await m.channel.send(res)

  async def analyze(self, guild, month, callback, status=None):
    date = datetime.datetime(month.year, month.month, 1) + datetime.timedelta(hours=4)
    dateEnd = datetime.datetime(month.year, month.month + 1, 1) + datetime.timedelta(hours=4)
    for channel in guild.text_channels:
      if not channel.permissions_for(guild.me).read_message_history:
        continue
      if status:
        await status.edit(content="Working... {}".format(channel.mention))
      async for message in channel.history(limit=None, after=date, before=dateEnd):
        if message.author.bot:
          continue
        callback(message)

  async def timeStats(self, guild, month, status=None):
    times = {}
    def _time(m):
      t = m.created_at - datetime.timedelta(hours=4)
      t = t.hour, t.minute // 30 * 3
      if t in times:
        times[t] += 1
      else:
        times[t] = 1
    await self.analyze(guild, month, _time, status)
    res = "```"
    for (h, m), count in sorted(times.items(), key=lambda kv: kv[0][0] * 10 + kv[0][1]):
      res += "{}:{}0 {}\n".format(h, m, "#" * math.ceil(count / 10))
    return res + "```"

  async def userStats(self, guild, month, status=None):
    users = {}
    def _user(m):
      if m.author in users:
        users[m.author] += 1
      else:
        users[m.author] = 1
    await self.analyze(guild, month, _user, status)
    res = ""
    for user, count in sorted(users.items(), key=lambda kv: kv[1], reverse=True):
      res += "{}#{}: {}\n".format(user.name, user.discriminator, count)
    return res

  async def channelStats(self, guild, month, status=None):
    channels = {}
    def _channel(m):
      if m.channel in channels:
        channels[m.channel] += 1
      else:
        channels[m.channel] = 1
    await self.analyze(guild, month, _channel, status)
    res = ""
    for channel, count in sorted(channels.items(), key=lambda kv: kv[1], reverse=True):
      res += "{}: {}\n".format(channel.mention, count)
    return res

  async def count(self, guild, month, status=None):
    users = {}
    channels = {}
    def _count(m):
      if m.author in users:
        users[m.author] += 1
      else:
        users[m.author] = 1
      if m.channel in channels:
        channels[m.channel] += 1
      else:
        channels[m.channel] = 1
    await self.analyze(guild, month, _count, status)
    res = ""
    for user, count in sorted(users.items(), key=lambda kv: kv[1], reverse=True):
      res += "{}#{}: {}\n".format(user.name, user.discriminator, count)
    res += "\n\n"
    for channel, count in sorted(channels.items(), key=lambda kv: kv[1], reverse=True):
      res += "{}: {}\n".format(channel.mention, count)
    return res

  async def monitor(self):
    while True:
      time = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
      for guild in self.guilds:
        async for audit in guild.audit_logs(limit=10):
          if audit.created_at < time:
            break
          if audit.user.id != owner and audit.user != audit.target and not audit.user.bot:
            if hasattr(audit.target, "mention"):
              target = audit.target.mention
            else:
              target = audit.target
            message = "User {} triggered {} on {}.".format(audit.user.mention, audit.action, target)
            await self.get_user(owner).send(message)
      await asyncio.sleep(5*60)

  async def rr(self, m):
    s = m.content.split()
    subcmd = s[1]
    if subcmd == "new":
      title = s[2]
      text = f"**{title}**\n"
      data = {"channel": m.channel.id}
      for i in range((len(s) - 3) // 2):
        emote, role = s[i * 2 + 3], s[i * 2 + 4]
        role = [r for r in m.guild.roles if r.name == role]
        if not role:
          return await m.channel.send("Invalid role {}".format(s[i + 4]))
        role = role[0]
        text += f"{emote} : `{role.name}`\n"
        data[emote] = role.id
      message = await m.channel.send(text[:-1])
      for emote in data.keys():
        if emote != "channel":
          await message.add_reaction(emote)
      self.reaction_roles[str(message.id)] = data
      with open("reaction_roles.json", "w") as f:
        f.write(json.dumps(self.reaction_roles))
    if subcmd == "edit":
      message_id = s[2]
      if message_id not in self.reaction_roles:
        return await m.channel.send("Invalid message ID.")
      channel = self.reaction_roles[message_id]["channel"]
      message = await self.get_channel(channel).fetch_message(int(message_id))
      data = {"channel": channel}
      text = message.content.split("\n")[0] + "\n"
      for i in range((len(s) - 3) // 2):
        emote, role = s[i * 2 + 3], s[i * 2 + 4]
        role = [r for r in m.guild.roles if r.name == role]
        if not role:
          return await m.channel.send("Invalid role {}".format(s[i + 4]))
        role = role[0]
        text += f"{emote} : `{role.name}`\n"
        data[emote] = role.id
      await message.edit(content=text)
      for emote in data.keys():
        if emote != "channel":
          await message.add_reaction(emote)
      self.reaction_roles[str(message.id)] = data
      with open("reaction_roles.json", "w") as f:
        f.write(json.dumps(self.reaction_roles))

  async def on_raw_reaction_add(self, payload):
    if str(payload.message_id) not in self.reaction_roles:
      return
    data = self.reaction_roles[str(payload.message_id)]
    if payload.emoji.is_custom_emoji():
      emote = "<:{}:{}>".format(payload.emoji.name, payload.emoji.id)
    else:
      emote = payload.emoji.name
    if emote in data:
      g = self.get_guild(payload.guild_id)
      user = g.get_member(payload.user_id)
      role = g.get_role(data[emote])
      if role not in user.roles:
        await user.add_roles(role)

  async def on_raw_reaction_remove(self, payload):
    if str(payload.message_id) not in self.reaction_roles:
      return
    data = self.reaction_roles[str(payload.message_id)]
    if payload.emoji.is_custom_emoji():
      emote = "<:{}:{}>".format(payload.emoji.name, payload.emoji.id)
    else:
      emote = payload.emoji.name
    if emote in data:
      g = self.get_guild(payload.guild_id)
      user = g.get_member(payload.user_id)
      role = g.get_role(data[emote])
      if role in user.roles:
        await user.remove_roles(role)

  async def on_raw_message_delete(self, payload):
    g = self.get_guild(payload.guild_id)
    entry = (await g.audit_logs(limit=1).flatten())[0]
    if entry.action == AuditLogAction.message_delete and entry.user.id != owner:
      channel = self.get_channel(payload.channel_id)
      if payload.cached_message:
        m = payload.cached_message.content + " "
      else:
        m = ""
      user = entry.user
      message = "User {} deleted message {}in channel {}.".format(user.mention, m, channel.mention)
      await self.get_user(owner).send(message)

  async def on_member_join(self, member):
    a = [r for r in member.guild.roles if r.name == "all"][0]
    await member.add_roles(a)

  async def exec(self, m):
    cmd = m.content
    if "```" in cmd:
      cmd = re.search(r"```([\s\S]*)```", cmd).group(1)
    cmd = "async def __exec(m):\n" + cmd.replace("\n", "\n  ")
    exec(cmd)
    await locals()["__exec"](m)

StatBot().run(token)
