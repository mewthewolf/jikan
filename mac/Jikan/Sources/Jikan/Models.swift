import Foundation

enum TrackingStatus: String {
    case idle = "Idle"
    case tracking = "Tracking"
    case processing = "Processing"
    case error = "Error"
}

struct SessionStartResponse: Decodable {
    let sessionId: Int
    let status: String
    let startedAt: Date

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case status
        case startedAt = "started_at"
    }
}

struct SessionStopResponse: Decodable {
    let sessionId: Int
    let status: String
    let endedAt: Date
    let reportId: Int?

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case status
        case endedAt = "ended_at"
        case reportId = "report_id"
    }
}

struct ReportResponse: Decodable, Identifiable {
    let id: Int
    let sessionId: Int
    let createdAt: Date
    let markdown: String
    let filePath: String
    let excludedNonWorkSeconds: Double

    enum CodingKeys: String, CodingKey {
        case id
        case sessionId = "session_id"
        case createdAt = "created_at"
        case markdown
        case filePath = "file_path"
        case excludedNonWorkSeconds = "excluded_non_work_seconds"
    }
}

struct SessionResponse: Decodable {
    let id: Int
    let startedAt: Date
    let endedAt: Date?
    let status: String
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case id
        case startedAt = "started_at"
        case endedAt = "ended_at"
        case status
        case errorMessage = "error_message"
    }
}

struct ActiveSessionResponse: Decodable {
    let activeSession: SessionResponse?

    enum CodingKeys: String, CodingKey {
        case activeSession = "active_session"
    }
}
