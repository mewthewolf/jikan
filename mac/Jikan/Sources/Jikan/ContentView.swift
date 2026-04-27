import SwiftUI

struct ContentView: View {
    @State private var viewModel = AppViewModel()

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            header
            controls
            reportPreview
        }
        .padding(24)
        .frame(minWidth: 880, minHeight: 640)
        .task {
            await viewModel.bootstrap()
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text("Jikan")
                    .font(.system(size: 30, weight: .semibold, design: .rounded))
                Text("Local session controller for ActivityWatch-based work reports")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            StatusBadge(status: viewModel.status)
        }
    }

    private var controls: some View {
        HStack(spacing: 16) {
            Button {
                Task { await viewModel.startSession() }
            } label: {
                Text("Start")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(viewModel.status == .tracking || viewModel.status == .processing)

            Button {
                Task { await viewModel.stopSession() }
            } label: {
                Text("Stop")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .controlSize(.large)
            .disabled(viewModel.status != .tracking)
        }
        .frame(maxWidth: 420)
        .overlay(alignment: .bottomLeading) {
            if let message = viewModel.errorMessage {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .offset(y: 26)
            }
        }
        .padding(.bottom, viewModel.errorMessage == nil ? 0 : 18)
    }

    private var reportPreview: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Latest Report")
                    .font(.title3.weight(.semibold))
                Spacer()
                if let report = viewModel.latestReport {
                    Text(report.createdAt.formatted(date: .abbreviated, time: .shortened))
                        .foregroundStyle(.secondary)
                }
            }

            Group {
                if let report = viewModel.latestReport {
                    ScrollView {
                        Text(report.markdown)
                            .font(.system(.body, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .textSelection(.enabled)
                    }
                } else if viewModel.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ContentUnavailableView(
                        "No Report Yet",
                        systemImage: "doc.text",
                        description: Text("Start and stop a session to generate the first report.")
                    )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(Color(nsColor: .windowBackgroundColor))
                    .shadow(color: .black.opacity(0.04), radius: 10, y: 3)
            )
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct StatusBadge: View {
    let status: TrackingStatus

    var body: some View {
        Text(status.rawValue)
            .font(.headline)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(color.opacity(0.14))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }

    private var color: Color {
        switch status {
        case .idle:
            return .secondary
        case .tracking:
            return .green
        case .processing:
            return .orange
        case .error:
            return .red
        }
    }
}
