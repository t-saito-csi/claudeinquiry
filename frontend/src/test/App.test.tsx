/**
 * App コンポーネントのテスト
 *
 * Red-Green-Refactor:
 *   - Red  : テストを先に書き、コンポーネントが期待通りに動作しないことを確認
 *   - Green: コンポーネントが正しくレンダリングされることを確認
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App', () => {
  it('サイトタイトルが表示されること', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: '問診システム' })).toBeInTheDocument()
  })

  it('ウェルカム見出しが表示されること', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: 'ようこそ' })).toBeInTheDocument()
  })

  it('3つのナビゲーションカード見出しが表示されること', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: '問診を始める' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '医師ダッシュボード' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '管理者画面' })).toBeInTheDocument()
  })

  it('患者向け・医師向け・管理者向けのバッジが表示されること', () => {
    render(<App />)
    expect(screen.getByText('患者向け')).toBeInTheDocument()
    expect(screen.getByText('医師向け')).toBeInTheDocument()
    expect(screen.getByText('管理者向け')).toBeInTheDocument()
  })

  it('3つのCTAボタンがレンダリングされること', () => {
    render(<App />)
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })

  it('AIサマリーは参考情報である旨のフッターが表示されること', () => {
    render(<App />)
    expect(screen.getByText(/AI分析は参考情報/)).toBeInTheDocument()
    expect(screen.getByText(/医師の診断を代替するものではありません/)).toBeInTheDocument()
  })
})
