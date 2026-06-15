import discord
from discord import app_commands
from datetime import datetime
import config

from config import AUTHORIZED_ASSIGN_ROLES


async def _safe_send(interaction: discord.Interaction, /, *args, **kwargs):
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        else:
            await interaction.followup.send(*args, **kwargs)
    except discord.NotFound:
        try:
            await interaction.followup.send(*args, **kwargs)
        except Exception:
            pass
    except Exception:
        pass


def is_authorized_for_remove(member: discord.Member) -> bool:
    """
    Check if the member has at least one of the authorized roles for using /remove_role
    """
    return any(role.id in AUTHORIZED_ASSIGN_ROLES for role in member.roles)


@app_commands.command(
    name="remove-role",
    description="Remove a role from a member (HR, Manager, Recruitment, CEO, or Founder only)"
)
@app_commands.describe(
    member="The member to remove the role from",
    role="The role to remove"
)
@app_commands.default_permissions(administrator=False)
async def remove_role(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    # Permission check
    if not is_authorized_for_remove(interaction.user):
        await _safe_send(
            interaction,
            "❌ You do not have permission to use this command.\n"
            "Only **HR Team**, **Manager**, **Recruitment Team**, **CEO**, or **Founder** can remove roles.",
            ephemeral=True,
        )
        return

    # Bot hierarchy check
    if role.position >= interaction.guild.me.top_role.position:
        await _safe_send(
            interaction,
            "❌ I cannot remove this role because it is higher than or equal to my highest role in the hierarchy.",
            ephemeral=True,
        )
        return

    # Check if member actually has the role
    if role not in member.roles:
        await _safe_send(
            interaction,
            f"⚠️ {member.mention} does not have the {role.mention} role.",
            ephemeral=True,
        )
        return

    # Attempt to remove the role
    try:
        await member.remove_roles(
            role,
            reason=f"Role removed by {interaction.user} ({interaction.user.id}) using /remove-role"
        )

        embed = discord.Embed(
            title="✅ Role Successfully Removed",
            description=f"{member.mention} has been removed from the {role.mention} role.",
            color=0xFF5A20,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.set_footer(text="NepPath | Role Management")

        await _safe_send(interaction, embed=embed)

        # Notify member via DM
        try:
            dm_embed = discord.Embed(
                title="🔕 Role Removed",
                description=f"The {role.mention} role has been removed from you in **{interaction.guild.name}**.",
                color=0xFF5A20
            )
            dm_embed.set_footer(text=f"Removed by {interaction.user}")
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # --- Announcement Logic ---
        if hasattr(config, "UPDATE_ROLES_CHANNEL_ID") and config.UPDATE_ROLES_CHANNEL_ID:
            ann_channel = interaction.guild.get_channel(config.UPDATE_ROLES_CHANNEL_ID)
            if ann_channel:
                # Calculate "To" role (Next highest after removal)
                remaining_roles = [r for r in member.roles if r.id != role.id and r.id != interaction.guild.id]
                remaining_roles.sort(key=lambda r: r.position, reverse=True)
                to_role = remaining_roles[0] if remaining_roles else interaction.guild.default_role

                is_demotion = role >= member.top_role
                title = "📉 User Demoted" if is_demotion else "📉 Role Removed"
                desc = f"⚠️ **{member.mention}** has been demoted." if is_demotion else f"⚠️ **{member.mention}** has been removed from **{role.name}**."

                ann_embed = discord.Embed(
                    title=title,
                    description=desc,
                    color=0xFF0000, # Red
                    timestamp=datetime.utcnow()
                )
                ann_embed.add_field(name="👤 User", value=member.mention, inline=True)
                ann_embed.add_field(name="🛡️ Staff", value=interaction.user.mention, inline=True)
                ann_embed.add_field(name="🔄 From", value=role.mention, inline=True)
                ann_embed.add_field(name="➡ To", value=to_role.mention, inline=True)

                if hasattr(config, "UPDATE_ROLES_CHANNEL_IMAGE_URL") and config.UPDATE_ROLES_CHANNEL_IMAGE_URL:
                    ann_embed.set_image(url=config.UPDATE_ROLES_CHANNEL_IMAGE_URL)
                
                footer_text = getattr(config, "FOOTER_TEXT", "NepPath")
                footer_icon = getattr(config, "FOOTER_ICON", config.AVATAR_URL)
                ann_embed.set_footer(text=footer_text, icon_url=footer_icon)
                
                if member.avatar:
                    ann_embed.set_thumbnail(url=member.avatar.url)
                elif member.guild.icon:
                    ann_embed.set_thumbnail(url=member.guild.icon.url)

                await ann_channel.send(embed=ann_embed)

    except discord.Forbidden:
        await _safe_send(
            interaction,
            "❌ I don't have permission to remove this role.\n"
            "Please ensure my role is above the target role in the role hierarchy and that I have the 'Manage Roles' permission.",
            ephemeral=True,
        )
    except Exception as e:
        await _safe_send(
            interaction,
            f"❌ An unexpected error occurred: `{str(e)}`",
            ephemeral=True,
        )


def setup(tree: app_commands.CommandTree):
    """
    Register the command with the bot's command tree.
    Call from `bot.py` like:
    from vtcs.removed import setup as setup_remove_role
    setup_remove_role(bot.tree)
    """
    tree.add_command(remove_role)
