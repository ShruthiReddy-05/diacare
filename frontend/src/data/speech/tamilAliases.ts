export const tamilNumberAliases: Record<string, string> = {
  ஒன்று: '1',
  ஓன்று: '1',
  இரண்டு: '2',
  ரெண்டு: '2',
  மூன்று: '3',
  முன்று: '3',
  நான்கு: '4',
  ஐந்து: '5',
  ஆறு: '6',
  ஏழு: '7',
  எட்டு: '8',
  ஒன்பது: '9',
  பத்து: '10',
  பதினொன்று: '11',
  பனிரெண்டு: '12',
  பதின்மூன்று: '13',
  பதினான்கு: '14',
  பதினைந்து: '15',
  இருபது: '20',
  முப்பது: '30',
  நாற்பது: '40',
  ஐம்பது: '50',
  அறுபது: '60',
  எழுபது: '70',
  எண்பது: '80',
  தொண்ணூறு: '90',
  நூறு: '100',
};

export const tamilConfirmationAliases: Record<string, string> = {
  ஆம்: 'yes',
  ஆமாம்: 'yes',
  சரி: 'yes',
  சரிதான்: 'yes',
  சம்மதம்: 'yes',
  சந்தோஷம்: 'yes',
  முடியும்: 'yes',
  வேண்டும்: 'yes',
  ஆமாங்க: 'yes',
  இல்லை: 'no',
  இல்ல: 'no',
  வேண்டாம்: 'no',
  முடியாது: 'no',
  கூடாது: 'no',
  பரவாயில்லை: 'no',
  அவசியமில்லை: 'no',
};

export const tamilGenderAliases: Record<string, string> = {
  ஆண்: 'male',
  ஆண: 'male',
  ஆம்பளை: 'male',
  பெண்: 'female',
  பெண: 'female',
  பொண்ணு: 'female',
  'ஆண் பெண் அல்லாத': 'other',
  மற்ற: 'other',
};

export const tamilExerciseAliases: Record<string, string> = {
  நடைபயிற்சி: 'walking',
  நடப்பது: 'walking',
  நட: 'walking',
  ஓட்டம்: 'jogging',
  ஓடுதல்: 'jogging',
  ஓடு: 'jogging',
  சைக்கிள்: 'cycling',
  சைக்கிளிங்: 'cycling',
  மிதிவண்டி: 'cycling',
  யோகா: 'yoga',
  யோக்கா: 'yoga',
  நீச்சல்: 'swimming',
  நீந்து: 'swimming',
  நடனம்: 'dancing',
  டான்ஸ்: 'dancing',
  'பளு தூக்குதல்': 'weightlifting',
  'எடை பயிற்சி': 'strength_training',
};

export const tamilScaleAliases: Record<string, string> = {
  பூஜ்யம்: '0',
  சுழி: '0',
  ஒன்று: '1',
  இரண்டு: '2',
  மூன்று: '3',
  நான்கு: '4',
  ஐந்து: '5',
  ஆறு: '6',
  ஏழு: '7',
  எட்டு: '8',
  ஒன்பது: '9',
  பத்து: '10',
  'மிகவும் குறைவு': '1',
  குறைவு: '2',
  சராசரி: '5',
  நிறைய: '8',
  'மிக அதிகம்': '10',
};

export function resolveTamilAlias(input: string): string {
  const cleaned = input.trim().toLowerCase().replace(/[.,!?]+$/, '');
  const allAliases = {
    ...tamilNumberAliases,
    ...tamilConfirmationAliases,
    ...tamilGenderAliases,
    ...tamilExerciseAliases,
    ...tamilScaleAliases,
  };
  if (allAliases[cleaned]) return allAliases[cleaned];
  if (allAliases[input.trim()]) return allAliases[input.trim()];
  return input;
}
