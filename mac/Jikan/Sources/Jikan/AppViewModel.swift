import Foundation
import Observation

@MainActor
@Observable
final class AppViewModel {
    var status: TrackingStatus = .idle
    var latestReport: ReportResponse?
    var errorMessage: String?
    var activeSessionID: Int?
    var isLoading = false

    private let apiClient: APIClient

    init(apiClient: APIClient = APIClient()) {
        self.apiClient = apiClient
    }

    func bootstrap() async {
        isLoading = true
        defer { isLoading = false }
        await refreshState()
    }

    func startSession() async {
        errorMessage = nil
        status = .tracking
        do {
            let response = try await apiClient.startSession()
            activeSessionID = response.sessionId
            status = .tracking
        } catch {
            status = .error
            errorMessage = error.localizedDescription
        }
    }

    func stopSession() async {
        errorMessage = nil
        status = .processing
        do {
            let response = try await apiClient.stopSession()
            activeSessionID = response.sessionId
            try await pollForReport(reportID: response.reportId)
            activeSessionID = nil
            status = .idle
        } catch {
            status = .error
            errorMessage = error.localizedDescription
        }
    }

    func refreshState() async {
        do {
            async let active = apiClient.fetchActiveSession()
            async let latestReport = apiClient.fetchLatestReport()
            let activeResponse = try await active
            self.latestReport = try await latestReport

            if let activeSession = activeResponse.activeSession {
                activeSessionID = activeSession.id
                status = activeSession.status == "processing" ? .processing : .tracking
                if activeSession.status == "error" {
                    status = .error
                    errorMessage = activeSession.errorMessage
                }
            } else {
                activeSessionID = nil
                if status != .error {
                    status = .idle
                }
            }
        } catch {
            status = .error
            errorMessage = error.localizedDescription
        }
    }

    private func pollForReport(reportID: Int?) async throws {
        for _ in 0 ..< 10 {
            if let reportID {
                if let report = try? await apiClient.fetchLatestReport(), report.id == reportID {
                    latestReport = report
                    return
                }
            } else if let report = try? await apiClient.fetchLatestReport() {
                latestReport = report
                return
            }
            try await Task.sleep(for: .seconds(1))
        }
        latestReport = try await apiClient.fetchLatestReport()
    }
}
