import client from "./client"

export const mcpAPI = {
  list: () => client.get("/mcp/services"),
  get: (id) => client.get(`/mcp/services/${id}`),
  create: (data) => client.post("/mcp/services", data),
  update: (id, data) => client.put(`/mcp/services/${id}`, data),
  delete: (id) => client.delete(`/mcp/services/${id}`),
  discover: (id) => client.post(`/mcp/services/${id}/discover`),
  execute: (id, toolName, args) =>
    client.post(`/mcp/services/${id}/execute`, {
      tool_name: toolName,
      arguments: args,
    }),
}
