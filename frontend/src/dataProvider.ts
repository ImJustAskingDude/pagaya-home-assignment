import { DataProvider, fetchUtils } from "react-admin";

import { apiUrl } from "./config";

type ApiListResponse<T> = {
  items: T[];
  total: number;
};

type ListQueryParams = {
  pagination?: {
    page: number;
    perPage: number;
  };
  sort?: {
    field: string;
    order: string;
  };
  filter?: Record<string, unknown>;
};

type HttpClientOptions = RequestInit & {
  headers?: HeadersInit;
};

const httpClient = (url: string, options: HttpClientOptions = {}) => {
  const headers = new Headers(options.headers ?? { Accept: "application/json" });
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetchUtils.fetchJson(url, { ...options, headers });
};

const buildListQuery = (params: ListQueryParams) => {
  const { page, perPage } = params.pagination ?? { page: 1, perPage: 25 };
  const { field, order } = params.sort ?? { field: "id", order: "ASC" };

  const search = new URLSearchParams({
    offset: String((page - 1) * perPage),
    limit: String(perPage),
    sort: field,
    order,
    filter: JSON.stringify(params.filter ?? {}),
  });

  return search.toString();
};

export const dataProvider: DataProvider = {
  async getList(resource, params) {
    const query = buildListQuery(params);
    const { json } = await httpClient(`${apiUrl}/${resource}?${query}`);
    const response = json as ApiListResponse<Record<string, unknown>>;
    return { data: response.items, total: response.total };
  },

  async getOne(resource, params) {
    const { json } = await httpClient(`${apiUrl}/${resource}/${params.id}`);
    return { data: json };
  },

  async getMany(resource, params) {
    const query = new URLSearchParams({
      limit: "100",
      filter: JSON.stringify({ ids: params.ids }),
    });
    const { json } = await httpClient(`${apiUrl}/${resource}?${query.toString()}`);
    const response = json as ApiListResponse<Record<string, unknown>>;
    return { data: response.items };
  },

  async getManyReference(resource, params) {
    const query = buildListQuery({
      ...params,
      filter: { ...params.filter, [params.target]: params.id },
    });
    const { json } = await httpClient(`${apiUrl}/${resource}?${query}`);
    const response = json as ApiListResponse<Record<string, unknown>>;
    return { data: response.items, total: response.total };
  },

  async create(resource, params) {
    const { json } = await httpClient(`${apiUrl}/${resource}`, {
      method: "POST",
      body: JSON.stringify(params.data),
    });
    return { data: json };
  },

  async update(resource, params) {
    const { json } = await httpClient(`${apiUrl}/${resource}/${params.id}`, {
      method: "PUT",
      body: JSON.stringify(params.data),
    });
    return { data: json };
  },

  async updateMany(resource, params) {
    const updates = await Promise.all(
      params.ids.map((id) =>
        httpClient(`${apiUrl}/${resource}/${id}`, {
          method: "PUT",
          body: JSON.stringify(params.data),
        }),
      ),
    );
    return { data: updates.map(({ json }) => json.id) };
  },

  async delete(resource, params) {
    const { json } = await httpClient(`${apiUrl}/${resource}/${params.id}`, {
      method: "DELETE",
    });
    return { data: json };
  },

  async deleteMany(resource, params) {
    const deletes = await Promise.all(
      params.ids.map((id) =>
        httpClient(`${apiUrl}/${resource}/${id}`, {
          method: "DELETE",
        }),
      ),
    );
    return { data: deletes.map(({ json }) => json.id) };
  },
};
