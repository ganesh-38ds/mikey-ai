with open('frontend/script.js', 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find('const langConfig = {')
end_idx = text.find('};\n\nfunction updateTopicButtons()')

new_config = '''const langConfig = {
  en: {
    voiceCode: 'en-IN',
    ttsLang: 'en-IN',
    placeholder: 'Enter your command...',
    voiceLabel: 'Voice Input',
    langLabel: 'English Mode Active',
    topics: {
      anime: 'Recommend a standout anime and provide a concise summary.',
      sports: 'Summarize the key sports developments of the week.',
      health: 'Offer three practical health tips for today.',
      study: 'Share efficient study strategies for focus and retention.',
      'fun facts': 'Provide three concise, surprising facts.',
      motivation: 'Offer a motivational message to stay productive.',
      productivity: 'Give three quick productivity hacks for a busy day.',
      tech: 'Explain one useful tech trend in simple terms.',
      travel: 'Suggest a short travel idea for a weekend escape.',
      movies: 'What are the latest movie releases, or recommend a great sports movie?'
    },
    topicLabels: ['Movies','Anime','Sports','Health','Study','Ideas','Motivation','Productivity','Tech','Travel'],
    topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],
    systemPrompt: `You are Shadowcall-AI — a professional, factual, and helpful AI assistant. Prioritize accuracy: if you are unsure about a fact, say "I may be mistaken" or "I don't know" rather than inventing details. Avoid fabricating events, quotes, or specifics. Keep replies concise, polite, and indicate when a claim should be verified.`
  },
  te: {
    voiceCode: 'te-IN',
    ttsLang: 'te-IN',
    placeholder: 'మీ కమాండ్ ఇవ్వండి...',
    voiceLabel: 'వాయిస్ ఇన్పుట్',
    langLabel: 'తెలుగు మోడ్ ఆక్టివ్',
    topics: {
      anime: 'ఒక మంచి యానిమే సిరీస్ గురించి చెప్పండి!',
      sports: 'ఈ వారం క్రీడా వార్తలు చెప్పండి?',
      health: 'ఈ రోజుకి ఒక 3 హెల్త్ టిప్స్ చెప్పండి!',
      study: 'చదువు కోసం మంచి టిప్స్ చెప్పండి!',
      'fun facts': '3 ఆసక్తికరమైన నిజాలు చెప్పండి!',
      motivation: 'నన్ను ఉత్తేజపరిచే ఒక కొటేషన్ చెప్పండి!',
      productivity: 'ఉత్పాదకత పెంచడానికి 3 టిప్స్.',
      tech: 'ఒక కొత్త టెక్ ట్రెండ్ గురించి సులభంగా చెప్పండి.',
      travel: 'ఈ వారాంతానికి వెళ్ళడానికి ఒక మంచి ప్రదేశం చెప్పండి.',
      movies: 'ఇటీవల విడుదలైన మంచి సినిమాలు చెప్పండి లేదా ఒక మంచి స్పోర్ట్స్ సినిమా సజెస్ట్ చేయండి.'
    },
    topicLabels: ['సినిమాలు','యానిమే','క్రీడలు','ఆరోగ్యం','చదువు','ఐడియాలు','మోటివేషన్','ఉత్పాదకత','టెక్','ట్రావెల్'],
    topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],
    systemPrompt: `మీరు Shadowcall-AI — ఒక ప్రొఫెషనల్, వాస్తవికమైన మరియు సహాయక AI. ఖచ్చితత్వానికి ప్రాధాన్యత ఇవ్వండి: ఒక వాస్తవం గురించి మీకు ఖచ్చితంగా తెలియకపోతే 'నాకు బహుశా తెలియకపోవచ్చు' లేదా 'నాకు తెలియదు' అని చెప్పండి, అంతేగానీ మీరే ఊహించి చెప్పకండి. సంభాషణలు సంక్షిప్తంగా, మర్యాదగా ఉంచండి మరియు ఒక వాదనను ఎప్పుడు ధృవీకరించాలో సూచించండి.\n\nCRITICAL INSTRUCTION: You MUST speak strictly in Telugu (and English if needed). ABSOLUTELY NO CHINESE, JAPANESE, OR KOREAN CHARACTERS ALLOWED.`
  }'''

if start_idx != -1 and end_idx != -1:
    new_text = text[:start_idx] + new_config + text[end_idx:]
    with open('frontend/script.js', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Done!')
else:
    print('Not found')
