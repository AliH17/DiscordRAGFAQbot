require('dotenv').config();
const {
  Client,
  GatewayIntentBits,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  EmbedBuilder,
  ModalBuilder,           // ← added
  TextInputBuilder,       // ← added
  TextInputStyle,         // ← added
  SlashCommandBuilder,
  REST,
  Routes
} = require('discord.js');
const fetch = require('node-fetch');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });


async function registerCommands() {
  const commands = [
    new SlashCommandBuilder()
      .setName('ask')
      .setDescription('Ask the RAG bot a question')
      .addStringOption(opt =>
        opt.setName('query')
           .setDescription('Your question')
           .setRequired(true)
      )
      .toJSON()
  ];

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    console.log('Registering slash commands…');
    await rest.put(
      Routes.applicationGuildCommands(
        process.env.CLIENT_ID,
        process.env.GUILD_ID
      ),
      { body: commands }
    );
    console.log('✅ Slash commands registered');
  } catch (err) {
    console.error('Failed to register commands:', err);
  }
}

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  await registerCommands();
});

// ───── Handle the /ask command ──────────────────────────────────────────────────
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand() || interaction.commandName !== 'ask') return;

  const query = interaction.options.getString('query');
  await interaction.deferReply(); // “thinking…”

  try {
    const res = await fetch(process.env.RAG_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // ─── ① Truncate long answers ───────────────────────────────
    let answer = data.answer;
    if (answer.length > 4000) {
      answer = answer.slice(0, 4000) + '\n…[truncated]';
    }

    // ─── Build the embed using `answer` (not data.answer) ───────
    const embed = new EmbedBuilder()
      .setTitle('🤖 FAQBOT Answer')
      .setDescription(answer)                            // ← use truncated `answer`
      .setColor(0x4F545C)
      .setFooter({ text: 'React below to let me know if this was helpful' });

    if (Array.isArray(data.sources) && data.sources.length) {
      embed.addFields({
        name: 'Sources',
        value: data.sources.map((s, i) => `${i+1}. ${s}`).join('\n')
      });
    }

    const feedbackRow = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('fb_positive')
        .setLabel('👍 Helpful')
        .setStyle(ButtonStyle.Success),
      new ButtonBuilder()
        .setCustomId('fb_negative')
        .setLabel('👎 Unhelpful')
        .setStyle(ButtonStyle.Danger)
    );

    await interaction.editReply({ embeds: [embed], components: [feedbackRow] });
  }
  catch (err) {
    // ─── ② Error‐state embed ────────────────────────────────────
    console.error('RAG fetch failed:', err);
    const errorEmbed = new EmbedBuilder()
      .setTitle('❌ Oops!')
      .setDescription('I couldn’t fetch an answer right now. Please try again later.')
      .setColor(0xFF0000);
    await interaction.editReply({ embeds: [errorEmbed] });
  }
});

// ───── Handle feedback buttons & modal ────────────────────────────────────────
client.on('interactionCreate', async interaction => {
  // 1) Modal submission (negative feedback with comments)
  if (interaction.isModalSubmit() && interaction.customId === 'feedback_modal') {
    const comment = interaction.fields.getTextInputValue('feedback_input');
    fetch(process.env.FEEDBACK_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messageId: interaction.message.id,
        userId: interaction.user.id,
        feedbackType: 'negative',
        comments: comment
      })
    }).catch(console.error);

    return interaction.reply({
      content: 'Thank you for your detailed feedback!',
      flags: 1 << 6
    });
  }

  // 2) Only buttons from here on
  if (!interaction.isButton()) return;

  // 3) Positive feedback
  if (interaction.customId === 'fb_positive') {
    fetch(process.env.FEEDBACK_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messageId: interaction.message.id,
        userId: interaction.user.id,
        feedbackType: 'positive'
      })
    }).catch(console.error);

    return interaction.reply({
      content: 'Thanks for your feedback!',
      flags: 1 << 6
    });
  }

  // 4) Negative feedback: show modal for comments
  if (interaction.customId === 'fb_negative') {
    const modal = new ModalBuilder()
      .setCustomId('feedback_modal')
      .setTitle('Sorry to hear that!');
    const input = new TextInputBuilder()
      .setCustomId('feedback_input')
      .setLabel('What could be improved?')
      .setStyle(TextInputStyle.Paragraph);
    modal.addComponents(new ActionRowBuilder().addComponents(input));
    return interaction.showModal(modal);
  }
});

client.login(process.env.DISCORD_TOKEN);
