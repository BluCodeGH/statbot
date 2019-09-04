import math
import datetime
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

  async def on_ready(self):
    print("Connected as " + str(self.user))

  async def on_message(self, m):
    if m.author == self.user:
      return
    if m.author.id == owner and m.content == "!quit":
      await self.logout()
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

StatBot().run(token)
