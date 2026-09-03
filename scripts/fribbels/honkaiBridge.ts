import { createInterface } from 'node:readline'
import { CharacterConverter, type UnconvertedCharacter } from 'lib/importer/characterConverter'
import { DEFAULT_TEAM } from 'lib/constants/constants'
import { getElementalDmgFromContainer, StatsToStatKey } from 'lib/scoring/simScoringUtils'
import { getSimScoreGrade } from 'lib/scoring/dpsScore'
import {
  executeOrchestrator,
  prepareOrchestrator,
  resolveSimulationMetadata,
} from 'lib/simulations/orchestrator/runDpsScoreBenchmarkOrchestrator'
import { getGameMetadata } from 'lib/state/gameMetadata'
import { Metadata } from 'lib/state/metadataInitializer'
import { ElementToDamage, PathNames, Stats } from 'lib/constants/constants'
import { ScoringConfigType } from 'types/metadata'

type BridgeRequest = {
  id?: string | number
  character: UnconvertedCharacter
  spdBenchmark?: number
  teammates?: Array<{
    characterId: string
    characterEidolon: number
    lightCone: string
    lightConeSuperimposition: number
    teamRelicSet?: string | null
    teamOrnamentSet?: string | null
  }>
}

Metadata.initialize()
globalThis.SEQUENTIAL_BENCHMARKS = true

// O protocolo reserva stdout para mensagens JSONL.
console.log = (...args: unknown[]) => console.error(...args)

async function calculate(request: BridgeRequest) {
  const converted = CharacterConverter.convert(request.character)
  const characterId = String(converted.id)
  const metadata = getGameMetadata().characters[characterId]
  if (!metadata) throw new Error(`Personagem ${characterId} não existe nos dados do Fribbels`)
  if (Object.keys(converted.equipped).length !== 6) {
    throw new Error('O DPS Benchmark exige seis relíquias válidas')
  }

  const simulation = resolveSimulationMetadata(
    converted,
    ScoringConfigType.DPS,
    DEFAULT_TEAM,
  )
  if (!simulation) throw new Error(`Personagem ${characterId} não possui DPS Benchmark`)
  if (request.teammates?.length) {
    simulation.teammates = request.teammates.map((teammate) => ({
      ...teammate,
      teamRelicSet: teammate.teamRelicSet || undefined,
      teamOrnamentSet: teammate.teamOrnamentSet || undefined,
    }))
  }

  const orchestrator = prepareOrchestrator(
    converted,
    { configType: ScoringConfigType.DPS, simulation },
    converted.equipped,
    { spdBenchmark: request.spdBenchmark },
  )
  await executeOrchestrator(orchestrator, { scoreOnly: false })
  orchestrator.calculateUpgrades()
  orchestrator.calculateResults()

  const original = orchestrator.originalSimResult!
  const combatStats = original.x.toComputedStatsObject() as Record<string, number>
  const elementalStat = ElementToDamage[metadata.element]
  combatStats[elementalStat] = getElementalDmgFromContainer(original.x, metadata.element)
  if (metadata.path === PathNames.Elation) {
    combatStats[Stats.Elation] = original.x.getSelfValue(StatsToStatKey[Stats.Elation])
  }

  const percent = orchestrator.percent!
  const substatUpgrades = (orchestrator.substatUpgradeResults ?? []).map((upgrade) => {
    const upgradedDamage = upgrade.simulationResult.simScore
    const projectedScore = (upgrade.percent ?? percent) * 100
    return {
      stat: upgrade.stat,
      damageGainPercent: original.simScore
        ? (upgradedDamage / original.simScore - 1) * 100
        : 0,
      scoreGainPercent: projectedScore - percent * 100,
      damageGain: upgradedDamage - original.simScore,
      projectedScore,
    }
  })
  const mainStatUpgrades = (orchestrator.mainUpgradeResults ?? []).map((upgrade) => {
    const upgradedDamage = upgrade.simulationResult.simScore
    const projectedScore = (upgrade.percent ?? percent) * 100
    return {
      part: upgrade.part,
      stat: upgrade.stat,
      damageGainPercent: original.simScore
        ? (upgradedDamage / original.simScore - 1) * 100
        : 0,
      scoreGainPercent: projectedScore - percent * 100,
      damageGain: upgradedDamage - original.simScore,
      projectedScore,
    }
  })
  return {
    id: request.id,
    ok: true,
    characterId,
    score: percent * 100,
    grade: getSimScoreGrade(percent, true, 6, !!converted.form.lightCone),
    damage: original.simScore,
    baseline: orchestrator.benchmarkBaselineScore!,
    benchmark: orchestrator.benchmarkSimScore!,
    perfection: Math.max(orchestrator.perfectionSimScore!, orchestrator.benchmarkSimScore!),
    combatStats,
    primaryActionStats: original.primaryActionStats ?? null,
    abilityBreakdown: (original.rotationDamage ?? []).map((step) => ({
      actionType: step.actionType,
      actionName: step.actionName,
      damage: step.damage,
    })),
    teammates: simulation.teammates,
    customTeam: !!request.teammates?.length,
    substatUpgrades,
    mainStatUpgrades,
  }
}

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
lines.on('line', async (line) => {
  if (!line.trim()) return
  let request: BridgeRequest | undefined
  try {
    request = JSON.parse(line) as BridgeRequest
    const result = await calculate(request)
    process.stdout.write(`${JSON.stringify(result)}\n`)
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      id: request?.id,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    })}\n`)
  }
})
