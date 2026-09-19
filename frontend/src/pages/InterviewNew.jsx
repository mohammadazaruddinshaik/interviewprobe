import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { createInterview } from '../api/interviews.js'
import Navbar from '../components/layout/Navbar.jsx'
import DifficultySelector from '../components/interview/DifficultySelector.jsx'
import QuestionCountSelector from '../components/interview/QuestionCountSelector.jsx'
import RoleSelector from '../components/interview/RoleSelector.jsx'
import TopicSelector from '../components/interview/TopicSelector.jsx'
import Button from '../components/ui/Button.jsx'
import { ArrowLeftIcon, BookIcon, ChartIcon, TargetIcon } from '../components/ui/icons.jsx'
import {
  DEFAULT_QUESTION_COUNT,
  DIFFICULTIES,
  MAX_QUESTIONS,
  MAX_TOPICS,
  MIN_QUESTIONS,
  MIN_TOPICS,
  ROLES,
} from '../data/interviewCatalog.js'

const BENEFITS = [
  {
    icon: TargetIcon,
    title: 'Realistic and adaptive',
    description: 'Questions adjust to your answers.',
  },
  {
    icon: ChartIcon,
    title: 'Focused practice',
    description: 'Target the skills you want to improve.',
  },
  {
    icon: BookIcon,
    title: 'Build confidence',
    description: 'Walk into your real interview prepared.',
  },
]

function InterviewNew() {
  const navigate = useNavigate()
  const [roleId, setRoleId] = useState(ROLES[0].id)
  const [difficulty, setDifficulty] = useState('MEDIUM')
  const [selectedTopics, setSelectedTopics] = useState([])
  const [questionCount, setQuestionCount] = useState(DEFAULT_QUESTION_COUNT)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)

  const role = ROLES.find((r) => r.id === roleId) ?? ROLES[0]
  const canStart = selectedTopics.length >= MIN_TOPICS

  function handleRoleChange(nextRoleId) {
    setRoleId(nextRoleId)
    setSelectedTopics([])
    setErrorMessage(null)
  }

  function handleToggleTopic(topicId) {
    setErrorMessage(null)
    setSelectedTopics((prev) => {
      if (prev.includes(topicId)) {
        return prev.filter((id) => id !== topicId)
      }
      if (prev.length >= MAX_TOPICS) {
        return prev
      }
      return [...prev, topicId]
    })
  }

  async function handleStart() {
    if (!canStart || isSubmitting) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const interview = await createInterview({
        role: roleId,
        difficulty,
        topics: selectedTopics,
        questionLimit: questionCount,
      })
      navigate(`/interview/${interview.id}`)
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : 'Something went wrong while creating your interview.',
      )
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-cream">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-cover bg-no-repeat opacity-90"
        style={{
          backgroundImage: 'url(/images/interview-setup-background.png)',
          backgroundPosition: 'left bottom',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-b from-cream/40 via-transparent to-cream/60"
      />

      <Navbar />

      <main className="mx-auto max-w-7xl px-6 pb-24 pt-10">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-ink/70 transition-colors duration-200 hover:text-ink"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to home
        </Link>

        <div className="mt-10 grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-start lg:gap-10">
          <div className="max-w-md lg:sticky lg:top-28">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
              Set up your interview
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Prepare for
              <br />
              <span className="text-accent">what&apos;s next.</span>
            </h1>
            <p className="mt-5 leading-relaxed text-muted">
              Choose the role, topics, and difficulty you want to practice. We&apos;ll adapt
              the interview to your responses and give you detailed feedback.
            </p>

            <ul className="mt-9 flex flex-col gap-6">
              {BENEFITS.map((benefit) => (
                <li key={benefit.title} className="flex items-start gap-3.5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                    <benefit.icon className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-ink">{benefit.title}</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-muted">
                      {benefit.description}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="motion-safe:animate-rise rounded-3xl border border-line/70 bg-cream-soft/80 p-6 shadow-xl shadow-ink/5 backdrop-blur-sm sm:p-8">
            <div className="flex items-start justify-between gap-4 border-b border-line/70 pb-5">
              <div>
                <h2 className="text-xl font-semibold text-ink sm:text-2xl">
                  Create a new interview
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">
                  Customize your interview experience. You can always change these later.
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-xs font-medium text-muted">Step 1 of 1</p>
                <div className="mt-2 h-1 w-14 rounded-full bg-accent" />
              </div>
            </div>

            <section className="border-b border-line/70 py-7">
              <SectionHeading index={1} title="Select role" subtitle="Choose the role you want to practice for." />
              <div className="mt-4">
                <RoleSelector roles={ROLES} value={roleId} onChange={handleRoleChange} />
              </div>
            </section>

            <section className="border-b border-line/70 py-7">
              <SectionHeading index={2} title="Select difficulty" subtitle="Choose the difficulty level." />
              <div className="mt-4">
                <DifficultySelector difficulties={DIFFICULTIES} value={difficulty} onChange={setDifficulty} />
              </div>
            </section>

            <section className="border-b border-line/70 py-7">
              <div className="flex items-start justify-between gap-4">
                <SectionHeading
                  index={3}
                  title="Select topics"
                  subtitle={`Choose ${MIN_TOPICS}–${MAX_TOPICS} topics to focus on.`}
                />
                <p className="shrink-0 pt-0.5 text-sm text-muted">
                  {selectedTopics.length} of {MAX_TOPICS} selected
                </p>
              </div>
              <div className="mt-4">
                <TopicSelector
                  topics={role.topics}
                  selected={selectedTopics}
                  onToggle={handleToggleTopic}
                  max={MAX_TOPICS}
                />
              </div>
            </section>

            <section className="flex flex-wrap items-center justify-between gap-4 py-7">
              <SectionHeading
                index={4}
                title="Number of questions"
                subtitle="Choose how many questions you want in this interview."
              />
              <div className="flex flex-col items-end gap-1">
                <QuestionCountSelector
                  value={questionCount}
                  onChange={setQuestionCount}
                  min={MIN_QUESTIONS}
                  max={MAX_QUESTIONS}
                />
                <p className="text-xs text-muted">
                  {MIN_QUESTIONS}–{MAX_QUESTIONS} questions
                </p>
              </div>
            </section>

            <div className="pt-1">
              <Button
                onClick={handleStart}
                disabled={!canStart || isSubmitting}
                aria-busy={isSubmitting}
                variant="inverse"
                withArrow={!isSubmitting}
                className="w-full justify-center"
              >
                {isSubmitting ? 'Starting interview…' : 'Start interview'}
              </Button>
              {!canStart && !errorMessage && (
                <p className="mt-3 text-center text-sm text-muted">
                  You must select at least one topic to start.
                </p>
              )}
              {errorMessage && (
                <p role="alert" aria-live="assertive" className="mt-3 text-center text-sm text-error">
                  {errorMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function SectionHeading({ index, title, subtitle }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
        {index}
      </span>
      <div>
        <h3 className="text-base font-semibold text-ink">{title}</h3>
        <p className="mt-0.5 text-sm text-muted">{subtitle}</p>
      </div>
    </div>
  )
}

export default InterviewNew
