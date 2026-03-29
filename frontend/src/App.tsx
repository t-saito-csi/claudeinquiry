/** 問診システム — トップページ */

type NavCard = {
  id: string
  title: string
  description: string
  badge: string
  badgeColor: string
  icon: string
  /** アクセシビリティ: スクリーンリーダー向け詳細説明 */
  ariaDescription: string
}

const NAV_CARDS: NavCard[] = [
  {
    id: 'patient',
    title: '問診を始める',
    description:
      'QRコードをスキャンして問診を開始します。スマートフォン・タブレットどちらからでもご利用いただけます。',
    badge: '患者向け',
    badgeColor: 'bg-green-100 text-green-800',
    icon: '📋',
    ariaDescription: 'QRコードスキャンで問診を開始する患者向けページへ移動します',
  },
  {
    id: 'dashboard',
    title: '医師ダッシュボード',
    description:
      '本日の予約患者一覧と問診完了状況を確認できます。AIサマリーも併せて表示されます。',
    badge: '医師向け',
    badgeColor: 'bg-blue-100 text-blue-800',
    icon: '🩺',
    ariaDescription: '本日の問診状況を確認する医師向けダッシュボードへ移動します',
  },
  {
    id: 'admin',
    title: '管理者画面',
    description:
      '診療科別フォームの作成・編集・公開、スタッフアカウントの管理を行えます。',
    badge: '管理者向け',
    badgeColor: 'bg-purple-100 text-purple-800',
    icon: '⚙️',
    ariaDescription: 'フォーム管理とスタッフ管理を行う管理者画面へ移動します',
  },
]

/** ナビゲーションカード — 各役割へのエントリーポイント */
function NavigationCard({ card }: { card: NavCard }) {
  return (
    <article
      className="
        bg-white rounded-2xl shadow-sm border border-gray-200
        p-8 flex flex-col gap-5
        hover:shadow-md hover:border-blue-300
        focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2
        transition-all duration-200
      "
      aria-label={card.ariaDescription}
    >
      {/* アイコン + バッジ */}
      <div className="flex items-start justify-between">
        <span
          className="text-5xl leading-none"
          role="img"
          aria-hidden="true"
        >
          {card.icon}
        </span>
        <span
          className={`
            inline-block px-3 py-1 rounded-full text-sm font-semibold
            ${card.badgeColor}
          `}
        >
          {card.badge}
        </span>
      </div>

      {/* テキスト */}
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold text-gray-900 leading-snug">
          {card.title}
        </h2>
        <p className="text-lg text-gray-600 leading-relaxed">
          {card.description}
        </p>
      </div>

      {/* CTA ボタン */}
      <div className="mt-auto pt-2">
        <button
          type="button"
          className="
            w-full py-4 px-6 rounded-xl
            bg-blue-600 text-white text-xl font-semibold
            hover:bg-blue-700 active:bg-blue-800
            focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600
            transition-colors duration-150
            /* WCAG 2.1 AA: タッチターゲット最小 44px を確保 */
            min-h-[3rem]
          "
          aria-label={card.ariaDescription}
        >
          {card.title}
        </button>
      </div>
    </article>
  )
}

/** ページヘッダー */
function Header() {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-5xl mx-auto px-6 py-5 flex items-center gap-4">
        <span className="text-3xl" role="img" aria-hidden="true">🏥</span>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">
            問診システム
          </h1>
          <p className="text-base text-gray-500 leading-snug">
            大規模病院向けデジタル問診
          </p>
        </div>
      </div>
    </header>
  )
}

/** ページフッター */
function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-auto">
      <div className="max-w-5xl mx-auto px-6 py-5 text-center text-base text-gray-500">
        <p>
          このシステムで提供されるAI分析は参考情報です。
          <strong className="text-gray-700">医師の診断を代替するものではありません。</strong>
        </p>
      </div>
    </footer>
  )
}

/** トップページ */
export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-12">
        {/* ページ説明 */}
        <section aria-labelledby="welcome-heading" className="mb-10 text-center">
          <h2
            id="welcome-heading"
            className="text-3xl font-bold text-gray-900 mb-3"
          >
            ようこそ
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            ご利用目的に応じてお選びください。
            問診の開始・診療状況の確認・システム管理が行えます。
          </p>
        </section>

        {/* ナビゲーションカード */}
        <section
          aria-label="利用目的の選択"
          className="
            grid gap-6
            grid-cols-1
            sm:grid-cols-2
            lg:grid-cols-3
          "
        >
          {NAV_CARDS.map((card) => (
            <NavigationCard key={card.id} card={card} />
          ))}
        </section>
      </main>

      <Footer />
    </div>
  )
}
