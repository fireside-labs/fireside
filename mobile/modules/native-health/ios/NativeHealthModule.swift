import ExpoModulesCore
import HealthKit

public class NativeHealthModule: Module {
    private let store = HKHealthStore()

    public func definition() -> ModuleDefinition {
        Name("NativeHealth")

        /// Request HealthKit permission — read-only, never writes
        AsyncFunction("requestPermission") { () -> Bool in
            guard HKHealthStore.isHealthDataAvailable() else { return false }

            let readTypes: Set<HKObjectType> = [
                HKQuantityType.quantityType(forIdentifier: .stepCount)!,
                HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!,
                HKQuantityType.quantityType(forIdentifier: .appleExerciseTime)!,
                HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!,
            ]

            return await withCheckedContinuation { continuation in
                self.store.requestAuthorization(toShare: nil, read: readTypes) { success, _ in
                    continuation.resume(returning: success)
                }
            }
        }

        /// Get step count for a specific date (ISO string)
        AsyncFunction("getSteps") { (dateString: String) -> Double in
            let granted = await self.requestHealthAccess()
            guard granted else { return 0 }

            let date = self.parseDate(dateString) ?? Date()
            return await self.querySum(
                type: HKQuantityType.quantityType(forIdentifier: .stepCount)!,
                unit: .count(),
                date: date
            )
        }

        /// Get sleep hours for a specific date (ISO string)
        AsyncFunction("getSleepHours") { (dateString: String) -> Double in
            let granted = await self.requestHealthAccess()
            guard granted else { return 0 }

            let date = self.parseDate(dateString) ?? Date()
            return await self.querySleepHours(date: date)
        }

        /// Get today's activity summary: steps, calories, active minutes
        AsyncFunction("getActivitySummary") { () -> [String: Double] in
            let granted = await self.requestHealthAccess()
            guard granted else {
                return ["steps": 0, "calories": 0, "activeMinutes": 0]
            }

            let today = Date()
            let steps = await self.querySum(
                type: HKQuantityType.quantityType(forIdentifier: .stepCount)!,
                unit: .count(),
                date: today
            )
            let calories = await self.querySum(
                type: HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!,
                unit: .kilocalorie(),
                date: today
            )
            let activeMinutes = await self.querySum(
                type: HKQuantityType.quantityType(forIdentifier: .appleExerciseTime)!,
                unit: .minute(),
                date: today
            )

            return [
                "steps": steps,
                "calories": calories,
                "activeMinutes": activeMinutes,
            ]
        }
    }

    // MARK: - Private Helpers

    private func requestHealthAccess() async -> Bool {
        guard HKHealthStore.isHealthDataAvailable() else { return false }

        let readTypes: Set<HKObjectType> = [
            HKQuantityType.quantityType(forIdentifier: .stepCount)!,
            HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!,
            HKQuantityType.quantityType(forIdentifier: .appleExerciseTime)!,
            HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!,
        ]

        return await withCheckedContinuation { continuation in
            store.requestAuthorization(toShare: nil, read: readTypes) { success, _ in
                continuation.resume(returning: success)
            }
        }
    }

    /// Sum quantity samples for a given day
    private func querySum(type: HKQuantityType, unit: HKUnit, date: Date) async -> Double {
        let cal = Calendar.current
        let start = cal.startOfDay(for: date)
        let end = cal.date(byAdding: .day, value: 1, to: start)!
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

        return await withCheckedContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, result, _ in
                let value = result?.sumQuantity()?.doubleValue(for: unit) ?? 0
                continuation.resume(returning: value)
            }
            self.store.execute(query)
        }
    }

    /// Query sleep analysis for total hours in bed
    private func querySleepHours(date: Date) async -> Double {
        let cal = Calendar.current
        let start = cal.startOfDay(for: date)
        let end = cal.date(byAdding: .day, value: 1, to: start)!
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
        let sleepType = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!

        return await withCheckedContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: sleepType,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: nil
            ) { _, samples, _ in
                guard let samples = samples as? [HKCategorySample] else {
                    continuation.resume(returning: 0)
                    return
                }

                // Sum durations of asleep samples
                let totalSeconds = samples
                    .filter { $0.value == HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue }
                    .reduce(0.0) { $0 + $1.endDate.timeIntervalSince($1.startDate) }

                continuation.resume(returning: totalSeconds / 3600.0)
            }
            self.store.execute(query)
        }
    }

    private func parseDate(_ string: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: string) { return date }
        // Fallback: try date-only format
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        return df.date(from: string)
    }
}
