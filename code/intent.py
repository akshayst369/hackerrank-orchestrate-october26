"""Local character n-gram classifier; no case IDs, answers, or network access."""
import re
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

# Participant-authored language examples, independent of sample status labels.
POSITIVE = [
    'Delete my account and personal data.', 'Erase all information about me.',
    'Close my profile permanently.', 'Remove my account from your systems.',
    'I request permanent deletion of my account.', 'Finish deleting my personal information.',
    'Check whether my account has been deleted.', 'Audit my previous deletion request.',
    'Verify that no personal information remains after account closure.',
    'I received deletion confirmation but my profile is still visible.',
    'Please remove the old search result for my deleted account.',
    'Remove personal details from my support conversations.',
    'Delete the downloadable export of my personal data.',
    'Retain the internal reference but erase my name and contact details.',
    'I no longer use the account and want it closed.',
    'Please ensure my earlier erasure request was completed.',
    'Solicito eliminar mi cuenta y mis datos personales.',
    'Quiero cerrar mi cuenta permanentemente.', 'Comprueben si se completó la eliminación.',
    'Je souhaite supprimer mon compte et mes données personnelles.',
    'Veuillez vérifier la suppression de mon compte.',
    'Solicito a exclusão da minha conta e dos meus dados.',
    'Por favor apague minha conta permanentemente.',
    'Bitte löschen Sie mein Konto und meine personenbezogenen Daten.',
    'Ich beantrage die endgültige Löschung meines Kontos.',
    'このアカウントと個人情報を完全に削除してください。',
    'アカウントの削除を依頼します。',
    '계정과 개인정보를 영구 삭제해 주세요.', '계정의 삭제를 요청합니다.',
    'أرجو حذف حسابي وجميع بياناتي الشخصية نهائياً.',
    'يرجى التأكد من اكتمال حذف الحساب.',
    'कृपया मेरा खाता और निजी डेटा स्थायी रूप से हटा दें।',
    'मैं अपने खाते को मिटाने का अनुरोध करता हूँ।',
    '请永久删除我的账户及个人资料。', '请核实账户删除是否完成。',
    'Elimina definitivamente il mio account e i miei dati.',
    'Lütfen hesabımı ve kişisel verilerimi silin.',
]
NEGATIVE = [
    'Send me a copy of my account data.', 'Export my personal information.',
    'I want to download my invoices.', 'Show me what information you hold about me.',
    'Correct my name on the account.', 'Change my email address.',
    'Update my phone number and keep my account active.',
    'Unsubscribe me from promotional emails.', 'Remove me from marketing lists only.',
    'Stop newsletters but keep my account.', 'Reset my password.',
    'Help me log into my profile.', 'Do not delete my account.',
    'Keep my account and purchase history.', 'This is not an erasure request.',
    'How does account deletion work?', 'Explain your retention policy.',
    'I am not asking for deletion.', 'Cancel my deletion request.',
    'Please leave my data unchanged.', 'Correct the spelling without removing my records.',
    'No eliminen mi cuenta, solo corrijan mi nombre.',
    'Envíenme una copia de mis datos.', 'Ne supprimez pas mon compte.',
    'Je souhaite une copie de mes informations.', 'Não excluam minha conta.',
    'Atualizem meu telefone.', 'Bitte mein Konto nicht löschen.',
    'Ich möchte meine Daten herunterladen.',
    'アカウントを削除しないでください。メールアドレスを変更したいです。',
    '계정을 삭제하지 마세요. 전화번호를 변경해 주세요.',
    'لا تحذف حسابي. أرسل نسخة من بياناتي.',
    'मेरा खाता मत हटाइए, केवल फोन नंबर बदलें।',
    '不要删除我的账户，请更改邮箱。', 'Non cancellate il mio account.',
]

def normalize(text):
    return unicodedata.normalize('NFKC', text).casefold().replace('’', "'")

class IntentModel:
    name = 'local-char-tfidf-logistic-regression-v1'
    def __init__(self):
        self.model = make_pipeline(
            TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), sublinear_tf=True),
            LogisticRegression(C=12, random_state=0, max_iter=1000),
        )
        self.model.fit([normalize(t) for t in POSITIVE + NEGATIVE],
                       [1] * len(POSITIVE) + [0] * len(NEGATIVE))
        self.calls = 0

    def classify(self, text):
        self.calls += 1
        t = normalize(text)
        score = float(self.model.predict_proba([t])[0][1])
        # Explicit refusal and restricted-scope opt-outs override statistical similarity.
        negative = re.search(
            r"(?:do not|don't|not asking for|not a request to|without)\s+(?:delete|close|erase|deletion|remov)"
            r"|(?:keep|leave).{0,45}(?:account|profile).{0,35}(?:active|as it is|in place)"
            r"|marketing lists only|cancel my deletion|not.{0,12}deletion|how (?:do|does|can).{0,30}delet"
            r"|ne supprimez pas|não exclu|nicht löschen|no elimin|削除しない|삭제하지|لا تحذف|不要删除|मत हट",
            t,
        )
        if negative:
            return False, score, 'explicit refusal or limited non-deletion scope'
        # High precision positive patterns cover audit requests and multilingual erasure.
        positive = re.search(
            r'\b(delet\w*|eras\w*|anonym\w*|elimin\w*|suppr\w*|exclus\w*|lösch\w*)\b'
            r'|(?:remove|close|closed).{0,75}(?:account|profile|personal|records|details)'
            r'|(?:account|profile).{0,60}(?:closed|gone|removed)'
            r'|削除|삭제|حذف|हटा|मिटा|删除', t
        )
        if positive:
            return True, score, 'erasure or deletion-audit intent'
        return score >= .5, score, 'local classifier'
