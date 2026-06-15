# associated.py
# Role Assignment Command: /assign-role
# Only usable by HR Team, Manager, Recruitment Team, CEO, or Founder

import discord
from discord import app_commands
from datetime import datetime
import config

# Import only the necessary config from your dedicated config.py
from config import AUTHORIZED_ASSIGN_ROLES

def is_authorized_for_assign(member: discord.Member) -> bool:
    """
    Check if the member has at least one of the authorized roles for using /assign-role
    """
    return any(role.id in AUTHORIZED_ASSIGN_ROLES for role in member.roles)


@app_commands.command(
    name="assign-role",
    description="Assign a role to a member (HR, Manager, Recruitment, CEO, or Founder only)"
)
@app_commands.describe(
    member="The member to assign the role to",
    role="The role to assign"
)
@app_commands.default_permissions(administrator=False)  # Optional visual hint
async def assign_role(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    """
    Slash command to assign a role to a user.
    Restricted to authorized management/HR roles.
    """
    # Permission check
    if not is_authorized_for_assign(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.\n"
            "Only **HR Team**, **Manager**, **Recruitment Team**, **CEO**, or **Founder** can assign roles.",
            ephemeral=True
        )
        return

    # Bot hierarchy check
    if role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "❌ I cannot assign this role because it is higher than or equal to my highest role in the hierarchy.",
            ephemeral=True
        )
        return

    # Check if member already has the role
    if role in member.roles:
        await interaction.response.send_message(
            f"⚠️ {member.mention} already has the {role.mention} role.",
            ephemeral=True
        )
        return

    # Attempt to assign the role
    try:
        await member.add_roles(
            role,
            reason=f"Role assigned by {interaction.user} ({interaction.user.id}) using /assign-role"
        )

        # Auto-remove conflicting driver roles
        driver_keywords = ["King Driver", "Master Driver", "Senior Driver", "Junior Driver", "Trainee Driver"]
        removed_text = ""
        
        # Check if the new role is a driver role
        if any(k in role.name for k in driver_keywords):
            roles_to_remove = []
            for r in member.roles:
                if r.id != role.id and any(k in r.name for k in driver_keywords):
                    roles_to_remove.append(r)
            
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason=f"Replaced by {role.name}")
                    removed_mentions = [r.mention for r in roles_to_remove]
                    removed_text = f"\n\n🗑️ **Auto-Removed:** {', '.join(removed_mentions)}"
                except Exception:
                    pass

        # Success embed
        embed = discord.Embed(
            title="✅ Role Successfully Assigned",
            description=f"{member.mention} has been given the {role.mention} role.{removed_text}",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Assigned By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Updated Role", value=role.mention, inline=True)
        embed.set_footer(text="NepPath | Role Management")

        await interaction.response.send_message(embed=embed)

        # Notify the member via DM (optional but nice)
        try:
            dm_embed = discord.Embed(
                title="🎉 Role Assigned!",
                description=f"You have been given the {role.mention} role in **{interaction.guild.name}**.",
                color=0x00FF00
            )
            dm_embed.set_footer(text=f"Assigned by {interaction.user}")
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

        # --- Announcement Logic ---
        if hasattr(config, "UPDATE_ROLES_CHANNEL_ID") and config.UPDATE_ROLES_CHANNEL_ID:
            ann_channel = interaction.guild.get_channel(config.UPDATE_ROLES_CHANNEL_ID)
            if ann_channel:
                # Check for Trainee
                if "trainee" in role.name.lower():
                    ann_embed = discord.Embed(
                        title="🚀 New Journey Started!",
                        description=f"🌟 Welcome **{member.mention}** to the team! Your journey as a **{role.name}** begins now.\n\n**Welcome aboard!**",
                        color=0xFF5A20,
                        timestamp=datetime.utcnow()
                    )
                    ann_embed.add_field(name="👤 User", value=member.mention, inline=True)
                    ann_embed.add_field(name="🛡️ Staff", value=interaction.user.mention, inline=True)
                    ann_embed.add_field(name="🔰 Role", value=role.mention, inline=True)
                else:
                    # Promotion / Assignment
                    # From: Current Top Role (before assignment)
                    from_role = member.top_role
                    
                    is_promotion = role > from_role
                    title = "📈 User Promoted" if is_promotion else "📈 Role Assigned"
                    desc = f"🎉 **{member.mention}** has been promoted!" if is_promotion else f"🎉 **{member.mention}** has been assigned **{role.name}**."

                    ann_embed = discord.Embed(
                        title=title,
                        description=desc,
                        color=0x00FF00, # Green
                        timestamp=datetime.utcnow()
                    )
                    ann_embed.add_field(name="<:contact:1397243449656475688> User", value=member.mention, inline=True)
                    ann_embed.add_field(name="<:admin:1397235968850923652> Staff", value=interaction.user.mention, inline=True)
                    ann_embed.add_field(name="<:info:1455400720173109382> From", value=from_role.mention, inline=True)
                    ann_embed.add_field(name="<a:right_hober1_1:1455424583493484676> To", value=role.mention, inline=True)

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
        await interaction.response.send_message(
            "❌ I don't have permission to assign this role.\n"
            "Please ensure my role is above the target role in the role hierarchy and that I have the 'Manage Roles' permission.",
            ephemeral=True
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"❌ An unexpected error occurred: `{str(e)}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ An unexpected error occurred: `{str(e)}`",
                ephemeral=True
            )


# Function to register the command with the bot's command tree
def setup(tree: app_commands.CommandTree):
    """
    Call this in your main bot.py to register the command:
    from associated import setup as setup_assign_role
    setup_assign_role(bot.tree)
    """
    # Register only the assign command here. The dedicated remove command
    # lives in `vtcs.removed` and is registered by its own setup function
    # to avoid duplicate registration of the same slash command name.
    tree.add_command(assign_role)