import Foundation

struct APIClient {
    let baseURL: URL

    init(baseURL: URL = URL(string: ProcessInfo.processInfo.environment["JIKAN_BACKEND_URL"] ?? "http://127.0.0.1:8000")!) {
        self.baseURL = baseURL
    }

    func startSession() async throws -> SessionStartResponse {
        try await request(path: "/sessions/start", method: "POST", responseType: SessionStartResponse.self)
    }

    func stopSession() async throws -> SessionStopResponse {
        try await request(path: "/sessions/stop", method: "POST", responseType: SessionStopResponse.self)
    }

    func fetchActiveSession() async throws -> ActiveSessionResponse {
        try await request(path: "/sessions/active", method: "GET", responseType: ActiveSessionResponse.self)
    }

    func fetchLatestReport() async throws -> ReportResponse? {
        let url = baseURL.appending(path: "/reports/latest")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        if data.trimmingCharacters(in: .whitespacesAndNewlines) == "null" {
            return nil
        }
        return try decoder.decode(ReportResponse.self, from: data)
    }

    private func request<Response: Decodable>(path: String, method: String, responseType: Response.Type) async throws -> Response {
        let url = baseURL.appending(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try decoder.decode(Response.self, from: data)
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200 ..< 300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown backend error"
            throw APIError.http(statusCode: httpResponse.statusCode, message: message)
        }
    }

    private var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case http(statusCode: Int, message: String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The backend returned an invalid response."
        case let .http(statusCode, message):
            return "HTTP \(statusCode): \(message)"
        }
    }
}

private extension Data {
    func trimmingCharacters(in set: CharacterSet) -> String {
        String(decoding: self, as: UTF8.self).trimmingCharacters(in: set)
    }
}
